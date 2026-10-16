"""STUB de autenticação do painel: `Authorization: Bearer <token do usuário>`.
Trocar pela dependência real do backend na integração."""

import hashlib

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import obter_db
from .modelos import Usuario


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Autenticação ausente")
    return authorization[7:].strip()


def usuario_atual(authorization: str | None = Header(None), db: Session = Depends(obter_db)) -> Usuario:
    u = db.scalar(select(Usuario).where(Usuario.token_hash == hash_token(bearer(authorization))))
    if u is None:
        raise HTTPException(401, "Usuário inválido")
    return u


def admin_atual(u: Usuario = Depends(usuario_atual)) -> Usuario:
    if u.papel != "admin":
        raise HTTPException(403, "Só administrador da loja")
    return u
