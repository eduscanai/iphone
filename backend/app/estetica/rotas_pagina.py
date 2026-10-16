"""Aparelho avaliado: eventos por long-poll (guia 7.4). O token da sessão é a credencial."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import obter_db
from . import eventos, sessoes

rotas = APIRouter(tags=["pagina"])


@rotas.get("/pagina/{token}/eventos")
async def eventos_pagina(token: str, apos: int = 0, db: Session = Depends(obter_db)):
    sessao_id = sessoes.sessao_por_token(db, token).id
    db.close()  # não segura conexão durante o long-poll
    return {"eventos": await eventos.aguardar(sessao_id, apos, ("tela",))}
