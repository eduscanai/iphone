"""Lado da cabine: abrir sessão, receber fotos, concluir e consultar a sugestão (guia 7.3)."""

import hashlib
import json
import random
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..base import auditoria
from ..base.modelos import Sessao
from ..config import config
from . import dimensoes, eventos, fila
from .armazenamento import TIPOS_MIME, armazenamento
from .enums import Face, Luz, ModoEstetica, Pose, StatusSessaoEstetica, TipoTarefa
from .modelos import (AvaliacaoEstetica, Cabine, ConfigEsteticaLoja, FotoEstetica, SessaoEstetica, SugestaoEstetica,
                      TarefaVisao)
from .roteiro import fotos_exigidas, roteiro

ASSINATURAS = {  # primeiros bytes de cada formato aceito
    "jpeg": (b"\xff\xd8\xff",),
    "heic": (b"ftypheic", b"ftypheix", b"ftyphevc", b"ftypmif1", b"ftypmsf1"),  # a partir do byte 4
    "dng": (b"II*\x00", b"MM\x00*"),
}


def agora():
    return datetime.now(timezone.utc)


def config_loja(db: Session, loja_id) -> ConfigEsteticaLoja:
    c = db.get(ConfigEsteticaLoja, loja_id)
    if c is None:
        c = ConfigEsteticaLoja(loja_id=loja_id, modo=ModoEstetica.desligado, percentual_cego=100)
        db.add(c)
        db.flush()
    return c


def conjunto_do_aparelho(chave: str) -> str:
    """Treino, validação ou teste, fixo por aparelho (hash do IMEI; guia 12.4).
    O conjunto de teste (holdout) nunca entra no treino e é onde o gate é medido."""
    h = int(hashlib.sha256(chave.encode()).hexdigest()[:8], 16) % 100
    p = config().estetica_percentual_holdout
    return "teste" if h < p else ("validacao" if h < p + 10 else "treino")


def sessao_por_token(db: Session, token: str) -> Sessao:
    s = db.scalar(select(Sessao).where(Sessao.token == token))
    if s is None or (s.expira_em is not None and s.expira_em < agora()):
        raise HTTPException(404, "Sessão inexistente ou expirada")
    return s


def _modelo(sessao: Sessao) -> dimensoes.Modelo:
    m = dimensoes.MODELOS.get(sessao.identificador_modelo or "")
    if m is None:
        raise HTTPException(422, f"Modelo {sessao.identificador_modelo or '(desconhecido)'} sem dimensões cadastradas")
    return m


def descrever_aparelho(sessao: Sessao) -> dict:
    m = _modelo(sessao)
    return {
        "identificador": sessao.identificador_modelo,
        "nome": m.nome,
        "cor": sessao.cor,
        "tela": m.tela,
        "dimensoes_mm": m.dimensoes_mm,
    }


def abrir(db: Session, cabine: Cabine, token: str, refazer: bool, sorteio=random.random) -> dict:
    sessao = sessao_por_token(db, token)
    if sessao.loja_id != cabine.loja_id:
        raise HTTPException(404, "Sessão inexistente ou expirada")
    cfg = config_loja(db, sessao.loja_id)
    if cfg.modo == ModoEstetica.desligado:
        raise HTTPException(403, "Nota estética desligada nesta loja")
    aparelho = descrever_aparelho(sessao)

    se = db.get(SessaoEstetica, sessao.id)
    if se is None:
        se = SessaoEstetica(
            sessao_id=sessao.id,
            cabine_id=cabine.id,
            status=StatusSessaoEstetica.capturando,
            cega=sorteio() * 100 < float(cfg.percentual_cego),
            conjunto=conjunto_do_aparelho(sessao.imei or str(sessao.id)),
            roteiro_versao=config().estetica_roteiro,
        )
        db.add(se)
        auditoria.registrar(db, "cabine", cabine.id, "estetica.sessao_aberta", "sessao", sessao.id, cega=se.cega)
    elif se.status == StatusSessaoEstetica.avaliada and not refazer:
        raise HTTPException(409, "Sessão já avaliada (use ?refazer=1 para nova captura)")
    elif refazer:
        se.status = StatusSessaoEstetica.capturando
        se.concluida_em = None
        se.cabine_id = cabine.id
        fila.cancelar_fusoes_pendentes(db, sessao.id)
        auditoria.registrar(db, "cabine", cabine.id, "estetica.refazer", "sessao", sessao.id)
    db.commit()
    return {
        "sessao_id": str(sessao.id),
        "aparelho": aparelho,
        "roteiro": roteiro(se.roteiro_versao),
        "mostrar_sugestao": not se.cega,
    }


def _passo(r: dict, ordem: int) -> dict:
    for p in r["passos"]:
        if p["ordem"] == ordem:
            return p
    raise HTTPException(422, f"Passo {ordem} não existe no roteiro {r['versao']}")


def _formato_confere(formato: str, dados: bytes) -> bool:
    if formato == "heic":
        return dados[4:12] in ASSINATURAS["heic"]
    return dados.startswith(ASSINATURAS[formato])


def receber_foto(db: Session, cabine: Cabine, token: str, idempotency_key: str, campos: dict, dados: bytes) -> dict:
    if not idempotency_key or len(idempotency_key) > 100:
        raise HTTPException(400, "Cabeçalho Idempotency-Key obrigatório")
    existente = db.scalar(select(FotoEstetica).where(FotoEstetica.idempotency_key == idempotency_key))
    if existente is not None:
        return {"foto_id": str(existente.id), "duplicada": True}

    sessao = sessao_por_token(db, token)
    se = db.get(SessaoEstetica, sessao.id)
    if se is None or sessao.loja_id != cabine.loja_id:
        raise HTTPException(404, "Sessão não aberta na cabine (chame GET /cabine/{token} antes)")
    if se.status == StatusSessaoEstetica.avaliada:
        raise HTTPException(409, "Sessão já avaliada")

    limite = config().estetica_tamanho_max_mb * 1024 * 1024
    if len(dados) > limite:
        raise HTTPException(413, f"Arquivo maior que {config().estetica_tamanho_max_mb} MB")
    formato = campos["formato"]
    if formato not in ASSINATURAS or not _formato_confere(formato, dados):
        raise HTTPException(422, "Arquivo não é HEIC, JPEG ou DNG válido")

    r = roteiro(se.roteiro_versao)
    passo = _passo(r, campos["passo"])
    try:
        face, luz, pose = Face(campos["face"]), Luz(campos["luz"]), Pose(campos["pose"])
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    if face != passo["faces"][0]:
        raise HTTPException(422, f"Face principal do passo {passo['ordem']} é {passo['faces'][0]}")
    if luz not in passo["luzes"] or pose != passo["pose"]:
        raise HTTPException(422, f"Luz ou pose fora do passo {passo['ordem']} do roteiro")

    meta = campos["metadados"]
    dims = meta.get("dimensoes_px") or {}
    foto_id = uuid.uuid4()
    chave = f"sessoes/{sessao.id}/fotos/{foto_id}.{'jpg' if formato == 'jpeg' else formato}"
    armazenamento().salvar(chave, dados, TIPOS_MIME[formato])
    foto = FotoEstetica(
        id=foto_id, sessao_id=sessao.id, passo=passo["ordem"], face=face, luz=luz, pose=pose,
        lado=campos.get("lado") or passo.get("lado"), tentativa=campos.get("tentativa") or 1, chave=chave,
        formato=formato, largura=int(dims.get("largura") or 0), altura=int(dims.get("altura") or 0),
        tamanho_bytes=len(dados), sha256=hashlib.sha256(dados).hexdigest(), metadados_camera=meta,
        qualidade_local=meta.get("qualidade_local"), idempotency_key=idempotency_key,
    )
    db.add(foto)
    try:
        db.flush()
    except IntegrityError:  # mesma chave chegou em paralelo
        db.rollback()
        armazenamento().apagar(chave)
        existente = db.scalar(select(FotoEstetica).where(FotoEstetica.idempotency_key == idempotency_key))
        return {"foto_id": str(existente.id), "duplicada": True}
    fila.criar(db, TipoTarefa.foto, sessao.id, foto.id)
    se.ultima_foto_em = agora()
    if se.status != StatusSessaoEstetica.capturando:  # foto refeita depois de concluir
        se.status = StatusSessaoEstetica.capturando
        se.concluida_em = None
        fila.cancelar_fusoes_pendentes(db, sessao.id)
    db.commit()
    return {"foto_id": str(foto.id), "duplicada": False}


def faltando(db: Session, sessao_id, r: dict) -> list[dict]:
    tem = set(db.execute(select(FotoEstetica.passo, FotoEstetica.luz).where(FotoEstetica.sessao_id == sessao_id)).all())
    return [{"passo": p, "luz": l} for p, l in sorted(fotos_exigidas(r) - {(a, b) for a, b in tem})]


def concluir(db: Session, cabine: Cabine, token: str, fotos_enviadas: int) -> dict:
    sessao = sessao_por_token(db, token)
    se = db.get(SessaoEstetica, sessao.id)
    if se is None or sessao.loja_id != cabine.loja_id:
        raise HTTPException(404, "Sessão não aberta na cabine")
    if se.status == StatusSessaoEstetica.avaliada:
        raise HTTPException(409, "Sessão já avaliada")
    falta = faltando(db, sessao.id, roteiro(se.roteiro_versao))
    if falta:
        raise HTTPException(409, {"mensagem": "Faltam fotos exigidas pelo roteiro", "faltando": falta})
    if se.concluida_em is None:
        se.concluida_em = agora()
        se.status = StatusSessaoEstetica.processando
        if not fila.pendentes_da_sessao(db, sessao.id, TipoTarefa.fusao):
            fila.criar(db, TipoTarefa.fusao, sessao.id)
        auditoria.registrar(db, "cabine", cabine.id, "estetica.captura_concluida", "sessao", sessao.id,
                            fotos_enviadas=fotos_enviadas)
    db.commit()
    return {"status": "processando"}


def pedir_tela(db: Session, cabine: Cabine, token: str, acao: str) -> None:
    sessao = sessao_por_token(db, token)
    if sessao.loja_id != cabine.loja_id:
        raise HTTPException(404, "Sessão inexistente ou expirada")
    eventos.emitir(db, sessao.id, "tela", {"acao": acao})
    db.commit()


def ultima_sugestao(db: Session, sessao_id) -> SugestaoEstetica | None:
    return db.scalar(
        select(SugestaoEstetica).where(SugestaoEstetica.sessao_id == sessao_id).order_by(SugestaoEstetica.criada_em.desc())
    )


def tem_avaliacao_final(db: Session, sessao_id) -> bool:
    return bool(db.scalar(select(func.count()).select_from(AvaliacaoEstetica).where(AvaliacaoEstetica.sessao_id == sessao_id)))


def faces_a_refazer(db: Session, sessao_id) -> list[str]:
    """Faces cuja última tentativa de alguma foto o worker reprovou."""
    fotos = db.scalars(
        select(FotoEstetica).where(FotoEstetica.sessao_id == sessao_id).order_by(FotoEstetica.criada_em)
    ).all()
    ultima: dict[tuple[int, str], FotoEstetica] = {}
    for f in fotos:
        ultima[(f.passo, f.luz)] = f
    return sorted({f.face for f in ultima.values() if f.aceita is False})


def estado_sugestao(db: Session, cabine: Cabine, token: str) -> dict:
    sessao = sessao_por_token(db, token)
    se = db.get(SessaoEstetica, sessao.id)
    if se is None or sessao.loja_id != cabine.loja_id:
        raise HTTPException(404, "Sessão não aberta na cabine")
    refazer = faces_a_refazer(db, sessao.id)
    if se.status == StatusSessaoEstetica.erro:
        return {"status": "erro", "mostrar": False, "refazer": refazer}
    sug = ultima_sugestao(db, sessao.id)
    if sug is None or se.status in (StatusSessaoEstetica.capturando, StatusSessaoEstetica.processando):
        st = "pendente" if se.status == StatusSessaoEstetica.capturando else "processando"
        return {"status": st, "mostrar": False, "refazer": refazer}
    if se.cega and not tem_avaliacao_final(db, sessao.id):
        return {"status": "pronta", "mostrar": False}
    resumo = [j for lista in sug.justificativas.values() for j in lista]
    return {
        "status": "pronta",
        "mostrar": True,
        "nota_final": sug.nota_final,
        "notas_por_face": sug.notas_por_face,
        "resumo": resumo,
        "refazer": refazer,
    }


def salvar_perfil(db: Session, cabine: Cabine, perfil: dict) -> None:
    if not isinstance(perfil.get("versao"), int):
        raise HTTPException(422, "Perfil sem versão inteira")
    cabine.perfil_calibracao = perfil
    auditoria.registrar(db, "cabine", cabine.id, "estetica.perfil_calibracao", "cabine", cabine.id,
                        versao=perfil["versao"])
    db.commit()


def ler_metadados(texto: str) -> dict:
    try:
        meta = json.loads(texto)
    except json.JSONDecodeError:
        raise HTTPException(422, "metadados não é JSON válido") from None
    if not isinstance(meta, dict):
        raise HTTPException(422, "metadados deve ser um objeto JSON")
    return meta


def tarefas_da_sessao(db: Session, sessao_id) -> list[TarefaVisao]:
    return list(db.scalars(select(TarefaVisao).where(TarefaVisao.sessao_id == sessao_id)))

