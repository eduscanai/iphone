"""Autenticação da cabine (token de pareamento, D10) e do worker de visão."""

import hashlib
import hmac
import secrets
import string

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..base.autenticacao import bearer
from ..config import config
from ..db import obter_db
from .modelos import Cabine

_ALFABETO_CODIGO = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1IL")


def hash_segredo(valor: str) -> str:
    return hashlib.sha256(valor.encode()).hexdigest()


def novo_token() -> str:
    return secrets.token_urlsafe(32)


def novo_codigo_pareamento() -> str:
    """Ex.: K7PQ-3XWD. Sem 0/O/1/I/L para não confundir na leitura."""
    c = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(8))
    return f"{c[:4]}-{c[4:]}"


def cabine_atual(authorization: str | None = Header(None), db: Session = Depends(obter_db)) -> Cabine:
    cab = db.scalar(select(Cabine).where(Cabine.token_hash == hash_segredo(bearer(authorization))))
    if cab is None or not cab.ativa:
        raise HTTPException(401, "Cabine não pareada ou revogada")
    return cab


def worker_atual(authorization: str | None = Header(None)) -> str:
    token = bearer(authorization)
    if not any(hmac.compare_digest(token, t) for t in config().tokens_worker):
        raise HTTPException(401, "Worker não autorizado")
    return token[:6]  # prefixo só para log; nunca o token inteiro
