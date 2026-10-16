"""Rotas do painel (guia 7.5): fila, sessão, critério, avaliação, concordância e configuração."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..base import auditoria
from ..base.autenticacao import admin_atual, usuario_atual
from ..base.modelos import Auditoria, Registro, Sessao, Usuario
from ..config import config
from ..db import obter_db
from . import avaliacao, concordancia, criterio, dimensoes, fila, gate
from .armazenamento import armazenamento
from .enums import ModoEstetica, StatusSessaoEstetica
from .esquemas import AvaliacaoEntrada, AvaliarCriterio, ConfigLoja
from .modelos import AvaliacaoEstetica, DefeitoEstetico, FotoEstetica, SessaoEstetica
from .sessoes import config_loja, tem_avaliacao_final, ultima_sugestao

rotas = APIRouter(tags=["painel"])


def _sessao_da_loja(db: Session, sessao_id, usuario: Usuario) -> tuple[Sessao, SessaoEstetica]:
    s = db.get(Sessao, sessao_id)
    se = db.get(SessaoEstetica, sessao_id)
    if s is None or se is None or s.loja_id != usuario.loja_id:
        raise HTTPException(404, "Sessão inexistente")
    return s, se


@rotas.get("/estetica/eu")
def eu(usuario: Usuario = Depends(usuario_atual)):
    """Quem está usando o painel (o painel mostra configuração e cabines só para o admin)."""
    return {"nome": usuario.nome, "papel": usuario.papel, "loja_id": str(usuario.loja_id)}


@rotas.get("/estetica/fila")
def fila_avaliacao(status: str = StatusSessaoEstetica.aguardando_tecnico, usuario: Usuario = Depends(usuario_atual),
                   db: Session = Depends(obter_db)):
    linhas = db.execute(
        select(SessaoEstetica, Sessao).join(Sessao, Sessao.id == SessaoEstetica.sessao_id)
        .where(Sessao.loja_id == usuario.loja_id, SessaoEstetica.status == status)
        .order_by(SessaoEstetica.iniciada_em)
    ).all()
    out = []
    for se, s in linhas:
        m = dimensoes.MODELOS.get(s.identificador_modelo or "")
        out.append({
            "sessao_id": str(s.id), "modelo": m.nome if m else s.identificador_modelo, "cor": s.cor,
            "iniciada_em": se.iniciada_em.isoformat(), "status": se.status, "cega": se.cega,
            "sugestao_pronta": se.sugestao_em is not None,
        })
    return out


def _defeito(d: DefeitoEstetico) -> dict:
    return {"id": str(d.id), "face": d.face, "tipo": d.tipo, "zona": d.zona, "visibilidade": d.visibilidade,
            "origem": d.origem, "estado": d.estado, "caixa_mm": d.caixa_mm, "geometria_mm": d.geometria_mm,
            "comprimento_mm": d.comprimento_mm, "area_mm2": d.area_mm2, "maior_dimensao_mm": d.maior_dimensao_mm,
            "confianca": d.confianca, "fonte": d.fonte, "foto_id": str(d.foto_id) if d.foto_id else None,
            "proposta_id": str(d.proposta_id) if d.proposta_id else None}


@rotas.get("/estetica/sessoes/{sessao_id}")
def detalhe(sessao_id: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)):
    s, se = _sessao_da_loja(db, sessao_id, usuario)
    arm = armazenamento()
    m = dimensoes.MODELOS.get(s.identificador_modelo or "")
    fotos = []
    for f in db.scalars(select(FotoEstetica).where(FotoEstetica.sessao_id == s.id).order_by(FotoEstetica.passo, FotoEstetica.criada_em)):
        faces = [g.get("face") for g in (f.geometria or [])]
        fotos.append({
            "foto_id": str(f.id), "passo": f.passo, "face": f.face, "luz": f.luz, "tentativa": f.tentativa,
            "aceita": f.aceita, "qualidade": f.qualidade_servidor, "faces_extraidas": faces,
            "original": arm.url_leitura(f.chave) if not f.original_apagada_em else None,
            "retificada": {fc: arm.url_leitura(f"{f.chave_retificada}_{fc}.jpg") for fc in faces} if f.chave_retificada else {},
            "anotada": {fc: arm.url_leitura(f"{f.chave_anotada}_{fc}.jpg") for fc in faces} if f.chave_anotada else {},
        })
    avaliada = tem_avaliacao_final(db, s.id)
    esconder = se.cega and not avaliada
    sug = ultima_sugestao(db, s.id)
    avaliacoes = db.scalars(select(AvaliacaoEstetica).where(AvaliacaoEstetica.sessao_id == s.id)
                            .order_by(AvaliacaoEstetica.criada_em)).all()
    ultima = avaliacoes[-1] if avaliacoes else None
    return {
        "sessao_id": str(s.id),
        "status": se.status,
        "cega": se.cega,
        "aparelho": {"identificador": s.identificador_modelo, "nome": m.nome if m else None, "cor": s.cor,
                     "dimensoes_mm": m.dimensoes_mm if m else None, "zonas_mm": m.zonas_mm() if m else {},
                     "raio_canto_mm": (m.raio_canto_mm or dimensoes.RAIO_PADRAO_MM) if m else None},
        "px_por_mm_retificacao": config().estetica_px_por_mm_retificacao,
        "fotos": fotos,
        "sugestao": None if esconder or sug is None else {
            "id": str(sug.id), "nota_final": sug.nota_final, "notas_por_face": sug.notas_por_face,
            "justificativas": sug.justificativas, "pendencias": sug.pendencias, "versao_visao": sug.versao_visao,
            "versao_criterio": sug.versao_criterio, "tempo_ms": sug.tempo_ms,
            "margem_minima": min((x["margem"] for x in sug.margens), default=None),
        },
        "defeitos_propostos": [] if esconder or sug is None else [
            _defeito(d) for d in db.scalars(select(DefeitoEstetico).where(DefeitoEstetico.sugestao_id == sug.id))],
        "avaliacoes": [{"id": str(a.id), "nota_final": a.nota_final, "nota_regra": a.nota_regra, "origem": a.origem,
                        "justificativa": a.justificativa, "criada_em": a.criada_em.isoformat(),
                        "notas_por_face": a.notas_por_face, "substitui_id": str(a.substitui_id) if a.substitui_id else None}
                       for a in avaliacoes],
        "defeitos_avaliacao": [_defeito(d) for d in db.scalars(
            select(DefeitoEstetico).where(DefeitoEstetico.avaliacao_id == ultima.id))] if ultima else [],
        "registro_id": str(r.id) if (r := db.scalar(select(Registro).where(Registro.sessao_id == s.id)
                                                    .order_by(Registro.criado_em.desc()))) else None,
    }


@rotas.post("/estetica/criterio/avaliar")
def avaliar_criterio(corpo: AvaliarCriterio, usuario: Usuario = Depends(usuario_atual)):
    c = criterio.carregar_versao(corpo.versao_criterio or criterio.VERSAO_ATUAL)
    entradas = [criterio.DefeitoEntrada(**d.model_dump()) for d in corpo.defeitos]
    return criterio.avaliar(entradas, c).como_dict()


@rotas.post("/registros/{registro_id}/estetica", status_code=201)
def salvar_avaliacao(registro_id: str, corpo: AvaliacaoEntrada, usuario: Usuario = Depends(usuario_atual),
                     db: Session = Depends(obter_db)):
    return avaliacao.salvar(db, registro_id, corpo, usuario)


@rotas.get("/estetica/concordancia")
def relatorio_concordancia(de: date | None = None, ate: date | None = None, modelo: str | None = None,
                           face: str | None = None, tecnico: str | None = None, incluir_nao_cegas: bool = False,
                           usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)):
    lista = concordancia.pares(db, loja_id=usuario.loja_id, de=de, ate=ate, modelo=modelo, tecnico_id=tecnico,
                               incluir_nao_cegas=incluir_nao_cegas)
    rel = concordancia.relatorio(lista, face)
    cfg = config_loja(db, usuario.loja_id)
    rel["gate"] = gate.avaliar(db, usuario.loja_id, cfg.sombra_iniciada_em)
    rel["aviso"] = ("Inclui sessões em que o técnico viu a sugestão: a concordância tende a sair inflada (R11)."
                    if incluir_nao_cegas else None)
    db.commit()
    return rel


@rotas.get("/estetica/config")
def ler_config(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)):
    cfg = config_loja(db, usuario.loja_id)
    db.commit()
    aviso = db.scalar(select(Auditoria).where(Auditoria.acao == "estetica.automatico_desligado",
                                             Auditoria.entidade_id == str(usuario.loja_id))
                      .order_by(Auditoria.quando.desc()))
    idade = fila.idade_da_mais_antiga_s(db)
    return {"modo": cfg.modo, "percentual_cego": float(cfg.percentual_cego),
            "sombra_iniciada_em": cfg.sombra_iniciada_em.isoformat() if cfg.sombra_iniciada_em else None,
            "ultimo_aviso": {"quando": aviso.quando.isoformat(), "motivos": aviso.dados.get("motivos")} if aviso else None,
            "fila_parada": idade is not None and idade > 300}


@rotas.put("/estetica/config")
def gravar_config(corpo: ConfigLoja, usuario: Usuario = Depends(admin_atual), db: Session = Depends(obter_db)):
    cfg = config_loja(db, usuario.loja_id)
    if corpo.modo == ModoEstetica.automatico and cfg.modo != ModoEstetica.automatico:
        g = gate.avaliar(db, usuario.loja_id, cfg.sombra_iniciada_em)
        if not g["passou"]:
            raise HTTPException(409, {"mensagem": "Gate do modo automático não atendido", "motivos": g["motivos"]})
    agora = datetime.now(timezone.utc)
    if corpo.percentual_cego >= 100 and (cfg.sombra_iniciada_em is None or float(cfg.percentual_cego) < 100):
        cfg.sombra_iniciada_em = agora
    elif corpo.percentual_cego < 100 and corpo.modo != ModoEstetica.automatico:
        cfg.sombra_iniciada_em = None
    auditoria.registrar(db, "usuario", usuario.id, "estetica.config", "loja", usuario.loja_id,
                        de={"modo": cfg.modo, "percentual_cego": float(cfg.percentual_cego)},
                        para=corpo.model_dump())
    cfg.modo, cfg.percentual_cego = corpo.modo, corpo.percentual_cego
    cfg.atualizado_por, cfg.atualizado_em = usuario.id, agora
    db.commit()
    return {"modo": cfg.modo, "percentual_cego": float(cfg.percentual_cego)}
