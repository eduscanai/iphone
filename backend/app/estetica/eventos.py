"""Eventos por sessão (guia 7.7): tabela + long-poll (consulta a cada 500 ms, até 25 s)."""

import asyncio
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import config
from ..db import nova_sessao
from .modelos import EventoSessao


def emitir(db: Session, sessao_id: uuid.UUID, tipo: str, dados: dict) -> None:
    """Sem commit: vai junto com a transação de quem chamou."""
    db.add(EventoSessao(sessao_id=sessao_id, tipo=tipo, dados=dados))


def _buscar(sessao_id, apos: int, tipos: tuple[str, ...]) -> list[dict]:
    with nova_sessao() as db:
        linhas = db.scalars(
            select(EventoSessao)
            .where(EventoSessao.sessao_id == sessao_id, EventoSessao.id > apos, EventoSessao.tipo.in_(tipos))
            .order_by(EventoSessao.id)
            .limit(100)
        ).all()
        return [{"seq": e.id, "tipo": e.tipo, "dados": e.dados} for e in linhas]


async def aguardar(sessao_id, apos: int, tipos: tuple[str, ...], limite_s: float | None = None) -> list[dict]:
    """Responde assim que houver evento novo, ou lista vazia no tempo-limite."""
    c = config()
    limite = time.monotonic() + (limite_s if limite_s is not None else c.estetica_long_poll_s)
    while True:
        eventos = await run_in_threadpool(_buscar, sessao_id, apos, tipos)
        if eventos or time.monotonic() >= limite:
            return eventos
        await asyncio.sleep(c.estetica_long_poll_intervalo_s)
