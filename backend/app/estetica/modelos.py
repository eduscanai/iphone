"""Tabelas da nota estética (guia 7.8). Enums ficam como `text` com CHECK na migração."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def _agora():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Cabine(Base):
    __tablename__ = "cabine"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    loja_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loja.id"), nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    ativa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    perfil_calibracao: Mapped[dict | None] = mapped_column(JSONB)  # guia 7.11; último enviado
    criada_em: Mapped[datetime] = _agora()
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CodigoPareamento(Base):
    __tablename__ = "cabine_pareamento"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    loja_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loja.id"), nullable=False)
    codigo_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    criado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessaoEstetica(Base):
    __tablename__ = "sessao_estetica"
    sessao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessao.id"), primary_key=True)
    cabine_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cabine.id"))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    cega: Mapped[bool] = mapped_column(Boolean, nullable=False)
    conjunto: Mapped[str] = mapped_column(Text, nullable=False)  # treino, validacao ou teste (hash do IMEI)
    roteiro_versao: Mapped[str] = mapped_column(Text, nullable=False)
    iniciada_em: Mapped[datetime] = _agora()
    ultima_foto_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sugestao_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avaliada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FotoEstetica(Base):
    __tablename__ = "foto_estetica"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    sessao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessao.id"), nullable=False)
    passo: Mapped[int] = mapped_column(Integer, nullable=False)
    face: Mapped[str] = mapped_column(Text, nullable=False)
    luz: Mapped[str] = mapped_column(Text, nullable=False)
    pose: Mapped[str] = mapped_column(Text, nullable=False)
    lado: Mapped[str | None] = mapped_column(Text)
    tentativa: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    chave: Mapped[str] = mapped_column(Text, nullable=False)
    formato: Mapped[str] = mapped_column(Text, nullable=False)
    largura: Mapped[int] = mapped_column(Integer, nullable=False)
    altura: Mapped[int] = mapped_column(Integer, nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    metadados_camera: Mapped[dict] = mapped_column(JSONB, nullable=False)
    qualidade_local: Mapped[dict | None] = mapped_column(JSONB)
    qualidade_servidor: Mapped[dict | None] = mapped_column(JSONB)
    aceita: Mapped[bool | None] = mapped_column(Boolean)
    geometria: Mapped[list | None] = mapped_column(JSONB)
    chave_retificada: Mapped[str | None] = mapped_column(Text)
    chave_anotada: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    original_apagada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # retenção
    criada_em: Mapped[datetime] = _agora()


class TarefaVisao(Base):
    __tablename__ = "tarefa_visao"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    sessao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessao.id"), nullable=False)
    foto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("foto_estetica.id"))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_id: Mapped[str | None] = mapped_column(Text)
    reservada_ate: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resultado: Mapped[dict | None] = mapped_column(JSONB)
    erro: Mapped[str | None] = mapped_column(Text)
    criada_em: Mapped[datetime] = _agora()
    atualizada_em: Mapped[datetime] = _agora()


class SugestaoEstetica(Base):
    __tablename__ = "sugestao_estetica"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    sessao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessao.id"), nullable=False)
    nota_final: Mapped[str] = mapped_column(String(1), nullable=False)
    notas_por_face: Mapped[dict] = mapped_column(JSONB, nullable=False)
    justificativas: Mapped[dict] = mapped_column(JSONB, nullable=False)
    margens: Mapped[list] = mapped_column(JSONB, nullable=False)
    pendencias: Mapped[list] = mapped_column(JSONB, nullable=False)
    versao_visao: Mapped[str] = mapped_column(Text, nullable=False)
    versao_criterio: Mapped[str] = mapped_column(Text, nullable=False)
    modelos: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tempo_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    criada_em: Mapped[datetime] = _agora()


class AvaliacaoEstetica(Base):
    """Só INSERT; correção = nova linha com `substitui_id`."""

    __tablename__ = "avaliacao_estetica"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    sessao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessao.id"), nullable=False)
    registro_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("registro.id"))
    nota_final: Mapped[str] = mapped_column(String(1), nullable=False)
    notas_por_face: Mapped[dict] = mapped_column(JSONB, nullable=False)
    nota_regra: Mapped[str] = mapped_column(String(1), nullable=False)
    justificativa: Mapped[str | None] = mapped_column(Text)
    origem: Mapped[str] = mapped_column(Text, nullable=False)
    cega: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tecnico_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))
    sugestao_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sugestao_estetica.id"))
    versao_criterio: Mapped[str] = mapped_column(Text, nullable=False)
    versao_visao: Mapped[str | None] = mapped_column(Text)
    substitui_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("avaliacao_estetica.id"))
    criada_em: Mapped[datetime] = _agora()


class DefeitoEstetico(Base):
    __tablename__ = "defeito_estetico"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    sessao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessao.id"), nullable=False)
    face: Mapped[str] = mapped_column(Text, nullable=False)
    foto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("foto_estetica.id"))
    fotos: Mapped[list | None] = mapped_column(JSONB)
    sugestao_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sugestao_estetica.id"))
    avaliacao_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("avaliacao_estetica.id"))
    proposta_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("defeito_estetico.id"))
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    zona: Mapped[str] = mapped_column(Text, nullable=False)
    visibilidade: Mapped[str] = mapped_column(Text, nullable=False)
    origem: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(Text, nullable=False)
    caixa_mm: Mapped[list] = mapped_column(JSONB, nullable=False)
    geometria_mm: Mapped[dict | None] = mapped_column(JSONB)
    comprimento_mm: Mapped[float | None] = mapped_column(Float)
    area_mm2: Mapped[float | None] = mapped_column(Float)
    maior_dimensao_mm: Mapped[float | None] = mapped_column(Float)
    confianca: Mapped[float | None] = mapped_column(Float)
    fonte: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = _agora()


class EventoSessao(Base):
    __tablename__ = "evento_sessao"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sessao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessao.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(Text, nullable=False)
    dados: Mapped[dict] = mapped_column(JSONB, nullable=False)
    criado_em: Mapped[datetime] = _agora()


class ConfigEsteticaLoja(Base):
    __tablename__ = "config_estetica_loja"
    loja_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loja.id"), primary_key=True)
    modo: Mapped[str] = mapped_column(Text, nullable=False, default="desligado")
    percentual_cego: Mapped[float] = mapped_column(Numeric, nullable=False, default=100)
    sombra_iniciada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # 100% cego desde
    atualizado_por: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id"))
    atualizado_em: Mapped[datetime] = _agora()
