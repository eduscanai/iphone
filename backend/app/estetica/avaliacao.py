"""Avaliação final pelo técnico (guia 7.5 e 7.8).

- Recalcula `nota_regra` com os defeitos confirmados + os desenhados pelo técnico.
- Exige justificativa se `nota_final` ≠ `nota_regra`.
- `origem = sugerida` só se tudo ficou igual à sugestão; senão `tecnico`.
- Propostas da máquina nunca mudam: cada avaliação grava cópias com o estado decidido.
- Só INSERT: correção = nova avaliação com `substitui_id`.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..base import auditoria
from ..base.modelos import Registro, Sessao, Usuario
from . import criterio, gate
from .enums import EstadoDefeito, Face, ModoEstetica, OrigemDefeito, OrigemNota, StatusSessaoEstetica
from .esquemas import AvaliacaoEntrada
from .modelos import AvaliacaoEstetica, DefeitoEstetico, SessaoEstetica
from .processamento import _copia
from .sessoes import config_loja, tem_avaliacao_final, ultima_sugestao


def agora():
    return datetime.now(timezone.utc)


def _entrada(d) -> criterio.DefeitoEntrada:
    return criterio.DefeitoEntrada(face=d.face, tipo=d.tipo, zona=d.zona, visibilidade=d.visibilidade,
                                   comprimento_mm=d.comprimento_mm, area_mm2=d.area_mm2,
                                   maior_dimensao_mm=d.maior_dimensao_mm)


def salvar(db: Session, registro_id, corpo: AvaliacaoEntrada, usuario: Usuario) -> dict:
    registro = db.get(Registro, registro_id)
    if registro is None or registro.sessao_id != corpo.sessao_id:
        raise HTTPException(404, "Registro inexistente ou de outra sessão")
    sessao = db.get(Sessao, corpo.sessao_id)
    if sessao.loja_id != usuario.loja_id:
        raise HTTPException(404, "Registro inexistente ou de outra sessão")
    se = db.get(SessaoEstetica, corpo.sessao_id)
    if se is None:
        raise HTTPException(409, "Sessão sem captura estética")
    if set(corpo.notas_por_face) != set(Face):
        raise HTTPException(422, "notas_por_face precisa das 6 faces")
    if corpo.substitui_id:
        anterior = db.get(AvaliacaoEstetica, corpo.substitui_id)
        if anterior is None or anterior.sessao_id != corpo.sessao_id:
            raise HTTPException(422, "substitui_id não pertence a esta sessão")

    sug = ultima_sugestao(db, corpo.sessao_id)
    # Sessão cega ainda sem avaliação: o técnico não viu a sugestão nem as propostas. Elas não
    # entram (nem como confirmadas, nem como rejeitadas) e a origem é sempre `tecnico` (R11).
    viu_sugestao = not (se.cega and not tem_avaliacao_final(db, corpo.sessao_id))
    propostas = ({p.id: p for p in db.scalars(select(DefeitoEstetico).where(DefeitoEstetico.sugestao_id == sug.id))}
                 if sug and viu_sugestao else {})

    decididas: dict = {}
    novos = []
    for d in corpo.defeitos:
        if d.novo is not None:
            novos.append(d.novo)
            continue
        p = propostas.get(d.proposta_id)
        if p is None:
            raise HTTPException(422, f"Proposta {d.proposta_id} não é da sugestão atual desta sessão")
        decididas[p.id] = d
    # Proposta sem decisão explícita conta como confirmada (o técnico não mexeu nela).
    finais = []
    mudou = bool(novos)
    for pid, p in propostas.items():
        d = decididas.get(pid)
        estado = d.estado if d else EstadoDefeito.confirmado
        mudancas = {k: getattr(d, k) for k in ("tipo", "zona", "visibilidade") if d and getattr(d, k) is not None}
        if estado == EstadoDefeito.rejeitado or any(str(v) != getattr(p, k) for k, v in mudancas.items()):
            mudou = True
        finais.append((p, estado, mudancas))

    entradas = [_entrada(_Mesclado(p, m)) for p, e, m in finais if e == EstadoDefeito.confirmado]
    entradas += [_entrada(n) for n in novos]
    res = criterio.avaliar(entradas)
    nota_regra = res.nota_final
    if corpo.nota_final != nota_regra and not (corpo.justificativa or "").strip():
        raise HTTPException(422, f"Justificativa obrigatória: a regra dá {nota_regra} e a nota informada é {corpo.nota_final}")

    notas = {str(k): str(v) for k, v in corpo.notas_por_face.items()}
    igual_sugestao = (viu_sugestao and sug is not None and not mudou and corpo.nota_final == sug.nota_final
                      and notas == sug.notas_por_face)
    av = AvaliacaoEstetica(
        sessao_id=corpo.sessao_id, registro_id=registro.id, nota_final=corpo.nota_final, notas_por_face=notas,
        nota_regra=nota_regra, justificativa=(corpo.justificativa or None),
        origem=OrigemNota.sugerida if igual_sugestao else OrigemNota.tecnico, cega=se.cega, tecnico_id=usuario.id,
        sugestao_id=sug.id if sug else None, versao_criterio=res.versao_criterio,
        versao_visao=sug.versao_visao if sug else None, substitui_id=corpo.substitui_id,
    )
    db.add(av)
    db.flush()
    for p, estado, mudancas in finais:
        db.add(_copia(p, av.id, estado, **mudancas))
    for n in novos:
        db.add(DefeitoEstetico(
            sessao_id=corpo.sessao_id, face=n.face, foto_id=n.foto_id, fotos=[str(n.foto_id)] if n.foto_id else None,
            avaliacao_id=av.id, tipo=n.tipo, zona=n.zona, visibilidade=n.visibilidade, origem=OrigemDefeito.tecnico,
            estado=EstadoDefeito.confirmado, caixa_mm=n.caixa_mm, geometria_mm=n.geometria_mm,
            comprimento_mm=n.comprimento_mm, area_mm2=n.area_mm2, maior_dimensao_mm=n.maior_dimensao_mm, fonte="tecnico",
        ))
    se.status = StatusSessaoEstetica.avaliada
    se.avaliada_em = agora()
    auditoria.registrar(db, "usuario", usuario.id, "estetica.avaliacao", "sessao", corpo.sessao_id,
                        avaliacao_id=av.id, nota_final=corpo.nota_final, nota_regra=nota_regra, origem=av.origem,
                        substitui_id=corpo.substitui_id)
    db.flush()
    if se.cega and config_loja(db, sessao.loja_id).modo == ModoEstetica.automatico:
        gate.monitorar(db, sessao.loja_id)
    db.commit()
    return {"avaliacao_id": str(av.id), "nota_regra": nota_regra, "origem": av.origem,
            "justificativas": {str(k): v for k, v in res.justificativas.items()}}


class _Mesclado:
    """Proposta com as mudanças do técnico (tipo, zona, visibilidade) aplicadas."""

    def __init__(self, p: DefeitoEstetico, mudancas: dict):
        self._p, self._m = p, mudancas

    def __getattr__(self, nome):
        return self._m.get(nome) or getattr(self._p, nome)
