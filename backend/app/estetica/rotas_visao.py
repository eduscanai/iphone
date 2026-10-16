"""Rotas do worker de visão (guia 7.6). O worker puxa tarefas por HTTPS (R14)."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from ..db import obter_db
from . import fila, processamento
from .esquemas import Falha, Renovar, Reservar
from .modelos import TarefaVisao
from .seguranca import worker_atual

rotas = APIRouter(prefix="/visao/tarefas", tags=["visao"])


@rotas.post("/reservar")
def reservar(corpo: Reservar, quem: str = Depends(worker_atual), db: Session = Depends(obter_db)):
    t = fila.reservar(db, corpo.worker_id, corpo.tipos)
    if t is None:
        return Response(status_code=204)
    return processamento.payload(db, t)


@rotas.post("/{tarefa_id}/renovar")
def renovar(tarefa_id: str, corpo: Renovar, quem: str = Depends(worker_atual), db: Session = Depends(obter_db)):
    t = db.get(TarefaVisao, tarefa_id)
    if t is None or not fila.renovar(db, t, corpo.worker_id):
        raise HTTPException(409, "Tarefa não está reservada por este worker")
    db.commit()
    return {"lease_ate": t.reservada_ate.isoformat()}


@rotas.post("/{tarefa_id}/resultado")
async def resultado(tarefa_id: str, request: Request, quem: str = Depends(worker_atual),
                    db: Session = Depends(obter_db)):
    return processamento.registrar_resultado(db, tarefa_id, await request.json(), quem)


@rotas.post("/{tarefa_id}/falha")
def falha(tarefa_id: str, corpo: Falha, quem: str = Depends(worker_atual), db: Session = Depends(obter_db)):
    return processamento.registrar_falha(db, tarefa_id, corpo.erro, corpo.recuperavel, corpo.worker_id, quem)
