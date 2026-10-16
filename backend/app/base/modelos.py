"""STUB: tabelas mínimas que o módulo estetica referencia (ver app/base/__init__.py)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Loja(Base):
    __tablename__ = "loja"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(Text)


class Usuario(Base):
    __tablename__ = "usuario"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    loja_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loja.id"))
    nome: Mapped[str] = mapped_column(Text)
    papel: Mapped[str] = mapped_column(String(20))  # tecnico ou admin
    token_hash: Mapped[str] = mapped_column(Text, unique=True)


class Sessao(Base):
    """Sessão de testes de um aparelho. O token vai no QR mostrado pelo aparelho."""

    __tablename__ = "sessao"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    loja_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loja.id"))
    token: Mapped[str] = mapped_column(Text, unique=True)
    identificador_modelo: Mapped[str | None] = mapped_column(Text)  # ProductType, ex.: iPhone14,5
    cor: Mapped[str | None] = mapped_column(Text)
    imei: Mapped[str | None] = mapped_column(Text)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Registro(Base):
    """Registro (laudo) gerado a partir de uma sessão."""

    __tablename__ = "registro"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    sessao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessao.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Auditoria(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    quando: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ator_tipo: Mapped[str] = mapped_column(String(20))  # usuario, cabine, worker, sistema
    ator_id: Mapped[str | None] = mapped_column(Text)
    acao: Mapped[str] = mapped_column(Text)
    entidade: Mapped[str] = mapped_column(Text)
    entidade_id: Mapped[str | None] = mapped_column(Text)
    dados: Mapped[dict] = mapped_column(JSONB, default=dict)
