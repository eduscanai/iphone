"""Esquemas de entrada e saída das rotas (guia, seção 7)."""

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import Face, Nota, TipoDefeito, Visibilidade, Zona


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- cabine (7.3)


class Concluir(_Estrito):
    fotos_enviadas: int = Field(ge=0)


class PedidoTela(_Estrito):
    acao: str = Field(pattern="^(preto|qr|normal)$")


class Ativar(_Estrito):
    codigo: str = Field(min_length=8, max_length=12)
    nome: str = Field(min_length=1, max_length=60)


# ---------------------------------------------------------------- worker (7.6, 7.9)


class Reservar(_Estrito):
    worker_id: str = Field(min_length=1, max_length=80)
    tipos: list[str] = ["foto", "fusao"]

    @field_validator("tipos")
    @classmethod
    def _tipos(cls, v):
        if not v or not set(v) <= {"foto", "fusao"}:
            raise ValueError("tipos deve conter foto e/ou fusao")
        return v


class Renovar(_Estrito):
    worker_id: str


class Falha(_Estrito):
    erro: str = Field(max_length=4000)
    recuperavel: bool = True
    worker_id: str | None = None


class Qualidade(BaseModel):
    ok: bool
    motivo: str | None = None
    nitidez: float | None = None
    estouro_pct: float | None = None
    contorno_ok: bool | None = None


class FaceExtraida(BaseModel):
    face: Face
    cantos_px: list[list[float]] = []
    homografia: list[list[float]] | None = None
    mm_por_px: float | None = None
    residuo_bordas_mm: float | None = None
    orientacao_ok: bool | None = None


class ResultadoFoto(BaseModel):
    tarefa_id: uuid.UUID
    tipo: str = Field(pattern="^foto$")
    foto_id: uuid.UUID
    versao_visao: str
    qualidade: Qualidade
    faces_extraidas: list[FaceExtraida] = []
    deteccoes: list[dict] = []
    artefatos: dict[str, bool] = {}
    tempo_ms: int = 0


class DefeitoFusao(BaseModel):
    face: Face
    tipo: TipoDefeito
    zona: Zona
    visibilidade: Visibilidade
    foto_principal: uuid.UUID | None = None
    fotos: list[uuid.UUID] = []
    caixa_mm: list[float] = Field(min_length=4, max_length=4)
    geometria_mm: dict | None = None
    comprimento_mm: float | None = None
    area_mm2: float | None = None
    maior_dimensao_mm: float | None = None
    confianca: float | None = Field(default=None, ge=0, le=1)
    fonte: str


class ResultadoFusao(BaseModel):
    tarefa_id: uuid.UUID
    tipo: str = Field(pattern="^fusao$")
    sessao_id: uuid.UUID
    versao_visao: str
    modelos: dict = {}
    defeitos: list[DefeitoFusao] = []
    faces_sem_foto_valida: list[Face] = []
    tempo_ms: int = 0


# ---------------------------------------------------------------- painel (7.5)


class DefeitoNovo(_Estrito):
    face: Face
    tipo: TipoDefeito
    zona: Zona
    visibilidade: Visibilidade
    caixa_mm: list[float] = Field(min_length=4, max_length=4)
    geometria_mm: dict | None = None
    comprimento_mm: float | None = Field(default=None, ge=0)
    area_mm2: float | None = Field(default=None, ge=0)
    maior_dimensao_mm: float | None = Field(default=None, ge=0)
    foto_id: uuid.UUID | None = None


class DecisaoDefeito(_Estrito):
    proposta_id: uuid.UUID | None = None
    estado: str | None = Field(default=None, pattern="^(confirmado|rejeitado)$")
    tipo: TipoDefeito | None = None
    zona: Zona | None = None
    visibilidade: Visibilidade | None = None
    novo: DefeitoNovo | None = None

    @model_validator(mode="after")
    def _um_ou_outro(self):
        if (self.novo is None) == (self.proposta_id is None):
            raise ValueError("informe proposta_id (com estado) ou novo, não os dois")
        if self.proposta_id is not None and self.estado is None:
            raise ValueError("decisão sobre proposta exige estado (confirmado ou rejeitado)")
        return self


class AvaliacaoEntrada(_Estrito):
    sessao_id: uuid.UUID
    notas_por_face: dict[Face, Nota]
    nota_final: Nota
    defeitos: list[DecisaoDefeito] = []
    justificativa: str | None = Field(default=None, max_length=2000)
    substitui_id: uuid.UUID | None = None


class DefeitoParaAvaliar(_Estrito):
    face: Face
    tipo: TipoDefeito
    zona: Zona
    visibilidade: Visibilidade
    comprimento_mm: float | None = None
    area_mm2: float | None = None
    maior_dimensao_mm: float | None = None


class AvaliarCriterio(_Estrito):
    defeitos: list[DefeitoParaAvaliar]
    versao_criterio: str | None = None


class ConfigLoja(_Estrito):
    modo: str = Field(pattern="^(desligado|assistido|automatico)$")
    percentual_cego: float = Field(ge=0, le=100)
