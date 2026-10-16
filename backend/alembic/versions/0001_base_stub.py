"""STUB: tabelas existentes do Morecheck (loja, usuario, sessao, registro, auditoria).

No repositório real elas já existem: na integração, NÃO portar esta migração; fazer a
0002 depender da última revisão real.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001_base_stub"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("loja", sa.Column("id", UUID, primary_key=True), sa.Column("nome", sa.Text, nullable=False))
    op.create_table(
        "usuario",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("loja_id", UUID, sa.ForeignKey("loja.id"), nullable=False),
        sa.Column("nome", sa.Text, nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
    )
    op.create_table(
        "sessao",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("loja_id", UUID, sa.ForeignKey("loja.id"), nullable=False),
        sa.Column("token", sa.Text, nullable=False, unique=True),
        sa.Column("identificador_modelo", sa.Text),
        sa.Column("cor", sa.Text),
        sa.Column("imei", sa.Text),
        sa.Column("criada_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "registro",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("sessao_id", UUID, sa.ForeignKey("sessao.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("quando", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ator_tipo", sa.String(20), nullable=False),
        sa.Column("ator_id", sa.Text),
        sa.Column("acao", sa.Text, nullable=False),
        sa.Column("entidade", sa.Text, nullable=False),
        sa.Column("entidade_id", sa.Text),
        sa.Column("dados", JSONB, nullable=False, server_default="{}"),
    )


def downgrade():
    for t in ("auditoria", "registro", "sessao", "usuario", "loja"):
        op.drop_table(t)
