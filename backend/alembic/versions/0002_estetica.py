"""Nota estética automática: tabelas da seção 7.8 do guia.

Acréscimos ao contrato (registrados no design.md): cabine.perfil_calibracao,
cabine_pareamento, sessao_estetica.conjunto, foto_estetica.original_apagada_em,
config_estetica_loja.sombra_iniciada_em.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0002_estetica"
down_revision = "0001_base_stub"
branch_labels = None
depends_on = None

FACES = ("frente", "traseira", "lat_esq", "lat_dir", "topo", "base")
LUZES = ("ambiente", "rasante_a", "rasante_b", "rasante_ab", "contraluz")
POSES = ("deitado", "lateral", "ponta")
TIPOS = ("risco", "trinca", "lascado", "amassado", "descascado", "desgaste", "mancha", "anomalia")
ZONAS = ("tela", "recorte_tela", "vidro_traseiro", "ilha_camera", "lente_camera", "moldura", "quina", "botao", "porta")
NOTAS = ("A", "B", "C", "D")


def _em(coluna, valores, nulo=False):
    lista = ", ".join(f"'{v}'" for v in valores)
    return f"{coluna} IS NULL OR {coluna} IN ({lista})" if nulo else f"{coluna} IN ({lista})"


def _agora(nome):
    return sa.Column(nome, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade():
    op.create_table(
        "cabine",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("loja_id", UUID, sa.ForeignKey("loja.id"), nullable=False),
        sa.Column("nome", sa.Text, nullable=False),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column("ativa", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("perfil_calibracao", JSONB),
        _agora("criada_em"),
        sa.Column("revogada_em", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "cabine_pareamento",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("loja_id", UUID, sa.ForeignKey("loja.id"), nullable=False),
        sa.Column("codigo_hash", sa.Text, nullable=False, unique=True),
        sa.Column("criado_por", UUID, sa.ForeignKey("usuario.id")),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_em", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "sessao_estetica",
        sa.Column("sessao_id", UUID, sa.ForeignKey("sessao.id"), primary_key=True),
        sa.Column("cabine_id", UUID, sa.ForeignKey("cabine.id")),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("cega", sa.Boolean, nullable=False),
        sa.Column("conjunto", sa.Text, nullable=False),
        sa.Column("roteiro_versao", sa.Text, nullable=False),
        _agora("iniciada_em"),
        sa.Column("ultima_foto_em", sa.DateTime(timezone=True)),
        sa.Column("concluida_em", sa.DateTime(timezone=True)),
        sa.Column("sugestao_em", sa.DateTime(timezone=True)),
        sa.Column("avaliada_em", sa.DateTime(timezone=True)),
        sa.CheckConstraint(_em("status", ("capturando", "processando", "aguardando_tecnico", "avaliada", "erro")), name="ck_sessao_estetica_status"),
        sa.CheckConstraint(_em("conjunto", ("treino", "validacao", "teste")), name="ck_sessao_estetica_conjunto"),
    )
    op.create_table(
        "foto_estetica",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("sessao_id", UUID, sa.ForeignKey("sessao.id"), nullable=False),
        sa.Column("passo", sa.Integer, nullable=False),
        sa.Column("face", sa.Text, nullable=False),
        sa.Column("luz", sa.Text, nullable=False),
        sa.Column("pose", sa.Text, nullable=False),
        sa.Column("lado", sa.Text),
        sa.Column("tentativa", sa.Integer, nullable=False, server_default="1"),
        sa.Column("chave", sa.Text, nullable=False),
        sa.Column("formato", sa.Text, nullable=False),
        sa.Column("largura", sa.Integer, nullable=False),
        sa.Column("altura", sa.Integer, nullable=False),
        sa.Column("tamanho_bytes", sa.BigInteger, nullable=False),
        sa.Column("sha256", sa.Text, nullable=False),
        sa.Column("metadados_camera", JSONB, nullable=False),
        sa.Column("qualidade_local", JSONB),
        sa.Column("qualidade_servidor", JSONB),
        sa.Column("aceita", sa.Boolean),
        sa.Column("geometria", JSONB),
        sa.Column("chave_retificada", sa.Text),
        sa.Column("chave_anotada", sa.Text),
        sa.Column("idempotency_key", sa.Text, nullable=False, unique=True),
        sa.Column("original_apagada_em", sa.DateTime(timezone=True)),
        _agora("criada_em"),
        sa.CheckConstraint(_em("face", FACES), name="ck_foto_face"),
        sa.CheckConstraint(_em("luz", LUZES), name="ck_foto_luz"),
        sa.CheckConstraint(_em("pose", POSES), name="ck_foto_pose"),
        sa.CheckConstraint(_em("lado", ("tela_cima", "tela_baixo"), nulo=True), name="ck_foto_lado"),
        sa.CheckConstraint(_em("formato", ("heic", "jpeg", "dng")), name="ck_foto_formato"),
    )
    op.create_index("ix_foto_estetica_sessao_passo_luz", "foto_estetica", ["sessao_id", "passo", "luz"])
    op.create_table(
        "tarefa_visao",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("sessao_id", UUID, sa.ForeignKey("sessao.id"), nullable=False),
        sa.Column("foto_id", UUID, sa.ForeignKey("foto_estetica.id")),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("tentativas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("worker_id", sa.Text),
        sa.Column("reservada_ate", sa.DateTime(timezone=True)),
        sa.Column("resultado", JSONB),
        sa.Column("erro", sa.Text),
        _agora("criada_em"),
        _agora("atualizada_em"),
        sa.CheckConstraint(_em("tipo", ("foto", "fusao")), name="ck_tarefa_tipo"),
        sa.CheckConstraint(_em("status", ("pendente", "reservada", "concluida", "falhou")), name="ck_tarefa_status"),
    )
    op.create_index("ix_tarefa_visao_status_criada", "tarefa_visao", ["status", "criada_em"])
    op.create_table(
        "sugestao_estetica",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("sessao_id", UUID, sa.ForeignKey("sessao.id"), nullable=False),
        sa.Column("nota_final", sa.CHAR(1), nullable=False),
        sa.Column("notas_por_face", JSONB, nullable=False),
        sa.Column("justificativas", JSONB, nullable=False),
        sa.Column("margens", JSONB, nullable=False),
        sa.Column("pendencias", JSONB, nullable=False),
        sa.Column("versao_visao", sa.Text, nullable=False),
        sa.Column("versao_criterio", sa.Text, nullable=False),
        sa.Column("modelos", JSONB, nullable=False),
        sa.Column("tempo_ms", sa.Integer, nullable=False),
        _agora("criada_em"),
        sa.CheckConstraint(_em("nota_final", NOTAS), name="ck_sugestao_nota"),
    )
    op.create_table(
        "avaliacao_estetica",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("sessao_id", UUID, sa.ForeignKey("sessao.id"), nullable=False),
        sa.Column("registro_id", UUID, sa.ForeignKey("registro.id")),
        sa.Column("nota_final", sa.CHAR(1), nullable=False),
        sa.Column("notas_por_face", JSONB, nullable=False),
        sa.Column("nota_regra", sa.CHAR(1), nullable=False),
        sa.Column("justificativa", sa.Text),
        sa.Column("origem", sa.Text, nullable=False),
        sa.Column("cega", sa.Boolean, nullable=False),
        sa.Column("tecnico_id", UUID, sa.ForeignKey("usuario.id")),
        sa.Column("sugestao_id", UUID, sa.ForeignKey("sugestao_estetica.id")),
        sa.Column("versao_criterio", sa.Text, nullable=False),
        sa.Column("versao_visao", sa.Text),
        sa.Column("substitui_id", UUID, sa.ForeignKey("avaliacao_estetica.id")),
        _agora("criada_em"),
        sa.CheckConstraint(_em("nota_final", NOTAS), name="ck_avaliacao_nota"),
        sa.CheckConstraint(_em("nota_regra", NOTAS), name="ck_avaliacao_nota_regra"),
        sa.CheckConstraint(_em("origem", ("tecnico", "sugerida", "automatica")), name="ck_avaliacao_origem"),
        sa.CheckConstraint("nota_final = nota_regra OR justificativa IS NOT NULL", name="ck_avaliacao_justificativa"),
    )
    op.create_table(
        "defeito_estetico",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("sessao_id", UUID, sa.ForeignKey("sessao.id"), nullable=False),
        sa.Column("face", sa.Text, nullable=False),
        sa.Column("foto_id", UUID, sa.ForeignKey("foto_estetica.id")),
        sa.Column("fotos", JSONB),
        sa.Column("sugestao_id", UUID, sa.ForeignKey("sugestao_estetica.id")),
        sa.Column("avaliacao_id", UUID, sa.ForeignKey("avaliacao_estetica.id")),
        sa.Column("proposta_id", UUID, sa.ForeignKey("defeito_estetico.id")),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("zona", sa.Text, nullable=False),
        sa.Column("visibilidade", sa.Text, nullable=False),
        sa.Column("origem", sa.Text, nullable=False),
        sa.Column("estado", sa.Text, nullable=False),
        sa.Column("caixa_mm", JSONB, nullable=False),
        sa.Column("geometria_mm", JSONB),
        sa.Column("comprimento_mm", sa.Float),
        sa.Column("area_mm2", sa.Float),
        sa.Column("maior_dimensao_mm", sa.Float),
        sa.Column("confianca", sa.Float),
        sa.Column("fonte", sa.Text, nullable=False),
        _agora("criado_em"),
        sa.CheckConstraint(_em("face", FACES), name="ck_defeito_face"),
        sa.CheckConstraint(_em("tipo", TIPOS), name="ck_defeito_tipo"),
        sa.CheckConstraint(_em("zona", ZONAS), name="ck_defeito_zona"),
        sa.CheckConstraint(_em("visibilidade", ("visivel", "so_rasante")), name="ck_defeito_visibilidade"),
        sa.CheckConstraint(_em("origem", ("maquina", "tecnico")), name="ck_defeito_origem"),
        sa.CheckConstraint(_em("estado", ("proposto", "confirmado", "rejeitado")), name="ck_defeito_estado"),
    )
    op.create_index("ix_defeito_estetico_sessao", "defeito_estetico", ["sessao_id"])
    op.create_table(
        "evento_sessao",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("sessao_id", UUID, sa.ForeignKey("sessao.id"), nullable=False),
        sa.Column("tipo", sa.Text, nullable=False),
        sa.Column("dados", JSONB, nullable=False),
        _agora("criado_em"),
    )
    op.create_index("ix_evento_sessao_sessao_id", "evento_sessao", ["sessao_id", "id"])
    op.create_table(
        "config_estetica_loja",
        sa.Column("loja_id", UUID, sa.ForeignKey("loja.id"), primary_key=True),
        sa.Column("modo", sa.Text, nullable=False, server_default="desligado"),
        sa.Column("percentual_cego", sa.Numeric, nullable=False, server_default="100"),
        sa.Column("sombra_iniciada_em", sa.DateTime(timezone=True)),
        sa.Column("atualizado_por", UUID, sa.ForeignKey("usuario.id")),
        _agora("atualizado_em"),
        sa.CheckConstraint(_em("modo", ("desligado", "assistido", "automatico")), name="ck_config_modo"),
        sa.CheckConstraint("percentual_cego >= 0 AND percentual_cego <= 100", name="ck_config_percentual"),
    )


def downgrade():
    for t in ("config_estetica_loja", "evento_sessao", "defeito_estetico", "avaliacao_estetica", "sugestao_estetica",
              "tarefa_visao", "foto_estetica", "sessao_estetica", "cabine_pareamento", "cabine"):
        op.drop_table(t)
