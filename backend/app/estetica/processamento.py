"""Lado do worker: montar as tarefas, receber resultados e gerar a sugestão (guia 7.6, 7.9, R13).

A visão devolve defeitos; quem aplica o critério e decide a nota é o backend.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..base import auditoria
from ..base.modelos import Sessao
from ..config import config
from . import criterio, dimensoes, eventos, fila
from .armazenamento import armazenamento
from .enums import (EstadoDefeito, ModoEstetica, OrigemDefeito, OrigemNota, StatusSessaoEstetica, StatusTarefa,
                    TipoDefeito, TipoTarefa)
from .esquemas import ResultadoFoto, ResultadoFusao
from .modelos import (AvaliacaoEstetica, Cabine, DefeitoEstetico, FotoEstetica, SessaoEstetica, SugestaoEstetica,
                      TarefaVisao)
from .roteiro import roteiro
from .sessoes import config_loja

# Detecção de trinca com confiança nessa faixa nunca vira nota automática (guia 13.3).
CONFIANCA_TRINCA_INTERMEDIARIA = (0.3, 0.8)


def agora():
    return datetime.now(timezone.utc)


def chave_artefato(foto: FotoEstetica, tipo: str, face: str) -> str:
    """Uma imagem retificada/anotada por face extraída da foto (com espelhos, uma foto tem 5 faces)."""
    return f"sessoes/{foto.sessao_id}/{tipo}/{foto.id}_{face}.jpg"


def _aparelho(db: Session, sessao_id) -> dict:
    sessao = db.get(Sessao, sessao_id)
    m = dimensoes.MODELOS[sessao.identificador_modelo]
    return {
        "identificador": sessao.identificador_modelo,
        "dimensoes_mm": m.dimensoes_mm,
        "raio_canto_mm": m.raio_canto_mm or dimensoes.RAIO_PADRAO_MM,
        "zonas_mm": m.zonas_mm(),
        "familia": dimensoes.familia(m, sessao.cor),
    }


def _config_worker() -> dict:
    c = config()
    return {"px_por_mm_retificacao": c.estetica_px_por_mm_retificacao,
            "versao_pipeline_minima": c.estetica_versao_pipeline_minima}


def _ultimas_fotos(db: Session, sessao_id) -> dict[tuple[int, str], FotoEstetica]:
    fotos = db.scalars(select(FotoEstetica).where(FotoEstetica.sessao_id == sessao_id).order_by(FotoEstetica.criada_em))
    ultima: dict[tuple[int, str], FotoEstetica] = {}
    for f in fotos:
        ultima[(f.passo, f.luz)] = f
    return ultima


def _faces_do_passo(se: SessaoEstetica, passo: int) -> list[str]:
    return next(p["faces"] for p in roteiro(se.roteiro_versao)["passos"] if p["ordem"] == passo)


def payload(db: Session, t: TarefaVisao) -> dict:
    """Tarefa como o worker recebe (guia 7.6)."""
    se = db.get(SessaoEstetica, t.sessao_id)
    base = {
        "tarefa_id": str(t.id),
        "tipo": t.tipo,
        "sessao_id": str(t.sessao_id),
        "lease_ate": t.reservada_ate.isoformat() if t.reservada_ate else None,
        "aparelho": _aparelho(db, t.sessao_id),
        "config": _config_worker(),
    }
    arm = armazenamento()
    if t.tipo == TipoTarefa.foto:
        f = db.get(FotoEstetica, t.foto_id)
        faces = _faces_do_passo(se, f.passo)
        irmas = [g for (p, _), g in _ultimas_fotos(db, t.sessao_id).items() if p == f.passo and g.id != f.id]
        cabine = db.get(Cabine, se.cabine_id) if se.cabine_id else None
        return base | {
            "foto": {"foto_id": str(f.id), "passo": f.passo, "face": f.face, "faces": faces, "luz": f.luz,
                     "pose": f.pose, "lado": f.lado, "url": arm.url_leitura(f.chave), "formato": f.formato,
                     "metadados": f.metadados_camera},
            "fotos_irmas": [{"foto_id": str(g.id), "luz": g.luz, "url": arm.url_leitura(g.chave), "formato": g.formato}
                            for g in irmas],
            "perfil_calibracao": (cabine.perfil_calibracao if cabine else None) or {},
            "upload": {
                tipo: {face: arm.url_escrita(chave_artefato(f, tipo, face), "image/jpeg") for face in faces}
                for tipo in ("retificada", "anotada")
            },
        }
    # fusão: resultados de todas as fotos válidas (última tentativa de cada passo e luz)
    fotos = []
    for (_, _), f in sorted(_ultimas_fotos(db, t.sessao_id).items()):
        tf = db.scalar(select(TarefaVisao).where(TarefaVisao.foto_id == f.id).order_by(TarefaVisao.criada_em.desc()))
        fotos.append({"foto_id": str(f.id), "passo": f.passo, "face": f.face, "faces": _faces_do_passo(se, f.passo),
                      "luz": f.luz, "pose": f.pose, "lado": f.lado, "aceita": f.aceita,
                      "resultado": tf.resultado if tf and tf.status == StatusTarefa.concluida else None})
    return base | {"roteiro": roteiro(se.roteiro_versao), "fotos": fotos}


def _tarefa_reservada(db: Session, tarefa_id, worker_id: str | None = None) -> TarefaVisao:
    t = db.get(TarefaVisao, tarefa_id)
    if t is None:
        raise HTTPException(404, "Tarefa inexistente")
    if t.status != StatusTarefa.reservada:
        raise HTTPException(409, f"Tarefa não está reservada (status {t.status})")
    if worker_id and t.worker_id != worker_id:
        raise HTTPException(409, "Tarefa reservada por outro worker")
    return t


def registrar_resultado(db: Session, tarefa_id, corpo: dict, quem: str) -> dict:
    t = _tarefa_reservada(db, tarefa_id)
    if t.tipo == TipoTarefa.foto:
        r = ResultadoFoto.model_validate(corpo)
        if r.foto_id != t.foto_id:
            raise HTTPException(422, "foto_id não confere com a tarefa")
        _resultado_foto(db, t, r)
    else:
        r = ResultadoFusao.model_validate(corpo)
        if r.sessao_id != t.sessao_id:
            raise HTTPException(422, "sessao_id não confere com a tarefa")
        _resultado_fusao(db, t, r)
    auditoria.registrar(db, "worker", quem, f"estetica.resultado_{t.tipo}", "tarefa_visao", t.id)
    db.commit()
    return {"ok": True}


def _resultado_foto(db: Session, t: TarefaVisao, r: ResultadoFoto) -> None:
    f = db.get(FotoEstetica, t.foto_id)
    f.qualidade_servidor = r.qualidade.model_dump()
    f.aceita = r.qualidade.ok
    f.geometria = [x.model_dump(mode="json") for x in r.faces_extraidas]
    if r.artefatos.get("retificada"):
        f.chave_retificada = f"sessoes/{f.sessao_id}/retificada/{f.id}"
    if r.artefatos.get("anotada"):
        f.chave_anotada = f"sessoes/{f.sessao_id}/anotada/{f.id}"
    fila.concluir(t, r.model_dump(mode="json"))
    if not r.qualidade.ok:
        eventos.emitir(db, f.sessao_id, "foto_reprovada",
                       {"foto_id": str(f.id), "face": f.face, "motivo": r.qualidade.motivo or "reprovada"})


def _obsoleta(db: Session, t: TarefaVisao) -> bool:
    """Chegou foto nova depois que esta fusão foi criada: o resultado não vale mais."""
    return db.scalar(
        select(FotoEstetica.id).where(FotoEstetica.sessao_id == t.sessao_id, FotoEstetica.criada_em > t.criada_em)
    ) is not None


def _resultado_fusao(db: Session, t: TarefaVisao, r: ResultadoFusao) -> None:
    fila.concluir(t, r.model_dump(mode="json"))
    if _obsoleta(db, t):
        t.erro = "obsoleta: fotos novas chegaram depois da fusão"
        return
    se = db.get(SessaoEstetica, t.sessao_id)
    entradas = [criterio.DefeitoEntrada(face=d.face, tipo=d.tipo, zona=d.zona, visibilidade=d.visibilidade,
                                        comprimento_mm=d.comprimento_mm, area_mm2=d.area_mm2,
                                        maior_dimensao_mm=d.maior_dimensao_mm, confianca=d.confianca)
                for d in r.defeitos]
    res = criterio.avaliar(entradas)
    pendencias = list(res.pendencias) + [f"{f}: sem foto válida" for f in r.faces_sem_foto_valida]
    inicio = se.ultima_foto_em or se.concluida_em or t.criada_em
    sug = SugestaoEstetica(
        sessao_id=t.sessao_id, nota_final=res.nota_final, notas_por_face={str(k): str(v) for k, v in res.notas_por_face.items()},
        justificativas={str(k): v for k, v in res.justificativas.items()},
        margens=[m.__dict__ | {"face": str(m.face)} for m in res.margens], pendencias=pendencias,
        versao_visao=r.versao_visao, versao_criterio=res.versao_criterio, modelos=r.modelos,
        tempo_ms=int((agora() - inicio).total_seconds() * 1000),
    )
    db.add(sug)
    db.flush()
    for d in r.defeitos:
        db.add(DefeitoEstetico(
            sessao_id=t.sessao_id, face=d.face, foto_id=d.foto_principal, fotos=[str(x) for x in d.fotos],
            sugestao_id=sug.id, tipo=d.tipo, zona=d.zona, visibilidade=d.visibilidade, origem=OrigemDefeito.maquina,
            estado=EstadoDefeito.proposto, caixa_mm=d.caixa_mm, geometria_mm=d.geometria_mm,
            comprimento_mm=d.comprimento_mm, area_mm2=d.area_mm2, maior_dimensao_mm=d.maior_dimensao_mm,
            confianca=d.confianca, fonte=d.fonte,
        ))
    se.sugestao_em = agora()
    se.status = StatusSessaoEstetica.aguardando_tecnico
    db.flush()
    if pode_automatizar(db, se, res, r, pendencias):
        avaliar_automaticamente(db, se, sug)
    eventos.emitir(db, t.sessao_id, "sugestao_pronta", {"sugestao_id": str(sug.id)})


def pode_automatizar(db: Session, se: SessaoEstetica, res: criterio.ResultadoNota, r: ResultadoFusao,
                     pendencias: list[str]) -> bool:
    """Automação seletiva (guia 13.3). Sessão cega vai sempre ao técnico (monitoramento)."""
    sessao = db.get(Sessao, se.sessao_id)
    if config_loja(db, sessao.loja_id).modo != ModoEstetica.automatico or se.cega:
        return False
    if pendencias or not res.automatizavel:
        return False
    lo, hi = CONFIANCA_TRINCA_INTERMEDIARIA
    for d in r.defeitos:
        if d.tipo == TipoDefeito.anomalia:
            return False
        if d.tipo == TipoDefeito.trinca and (d.confianca is None or lo <= d.confianca <= hi):
            return False
    return True


def avaliar_automaticamente(db: Session, se: SessaoEstetica, sug: SugestaoEstetica) -> AvaliacaoEstetica:
    av = AvaliacaoEstetica(
        sessao_id=se.sessao_id, nota_final=sug.nota_final, notas_por_face=sug.notas_por_face, nota_regra=sug.nota_final,
        origem=OrigemNota.automatica, cega=False, tecnico_id=None, sugestao_id=sug.id,
        versao_criterio=sug.versao_criterio, versao_visao=sug.versao_visao,
    )
    db.add(av)
    db.flush()
    for p in db.scalars(select(DefeitoEstetico).where(DefeitoEstetico.sugestao_id == sug.id)):
        db.add(_copia(p, av.id, EstadoDefeito.confirmado))
    se.status = StatusSessaoEstetica.avaliada
    se.avaliada_em = agora()
    auditoria.registrar(db, "sistema", None, "estetica.nota_automatica", "sessao", se.sessao_id, nota=sug.nota_final)
    return av


def _copia(p: DefeitoEstetico, avaliacao_id, estado: str, **mudancas) -> DefeitoEstetico:
    return DefeitoEstetico(
        sessao_id=p.sessao_id, face=p.face, foto_id=p.foto_id, fotos=p.fotos, avaliacao_id=avaliacao_id,
        proposta_id=p.id, tipo=mudancas.get("tipo") or p.tipo, zona=mudancas.get("zona") or p.zona,
        visibilidade=mudancas.get("visibilidade") or p.visibilidade, origem=p.origem, estado=estado,
        caixa_mm=p.caixa_mm, geometria_mm=p.geometria_mm, comprimento_mm=p.comprimento_mm, area_mm2=p.area_mm2,
        maior_dimensao_mm=p.maior_dimensao_mm, confianca=p.confianca, fonte=p.fonte,
    )


def registrar_falha(db: Session, tarefa_id, erro: str, recuperavel: bool, worker_id: str | None, quem: str) -> dict:
    t = _tarefa_reservada(db, tarefa_id, worker_id)
    fila.falhar(t, erro, recuperavel)
    if t.status == StatusTarefa.falhou:
        if t.tipo == TipoTarefa.fusao:
            se = db.get(SessaoEstetica, t.sessao_id)
            se.status = StatusSessaoEstetica.erro
        else:
            f = db.get(FotoEstetica, t.foto_id)
            eventos.emitir(db, t.sessao_id, "foto_reprovada",
                           {"foto_id": str(f.id), "face": f.face, "motivo": "erro no processamento"})
    auditoria.registrar(db, "worker", quem, "estetica.falha_tarefa", "tarefa_visao", t.id,
                        recuperavel=recuperavel, status=t.status)
    db.commit()
    return {"status": t.status}
