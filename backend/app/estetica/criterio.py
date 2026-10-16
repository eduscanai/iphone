"""Motor de critério da nota estética (guia, seção 16).

`avaliar(defeitos, criterio)` é uma função pura: sem banco, sem rede, sem relógio.
Mesma entrada → mesma saída. As regras ficam em YAML versionado (`criterios/`).

Semântica (guia 16.3):
1. Entram os defeitos com estado diferente de `rejeitado`.
2. Por face e por grupo de zonas, percorre a lista de regras (da pior nota para a melhor);
   a nota do grupo é a da primeira regra que casar, ou o `padrao`.
3. Nota da face = pior entre os grupos, depois `gerais.no_minimo`. Face sem defeitos = A.
4. Nota final = pior face.
5. Margens: distância relativa entre o valor observado e cada limite numérico das regras
   cujos filtros casam com algum defeito. Margem < 10% impede a nota automática.
6. Regra `a_definir` decisiva, anomalia que exige revisão ou tipo sem regra no grupo
   → `pendencias` (nunca vira nota automática).
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import ORDEM_NOTA, EstadoDefeito, Face, Nota, TipoDefeito, Visibilidade, Zona, pior

DIR_CRITERIOS = Path(__file__).parent / "criterios"
MARGEM_AUTOMATICO = 0.10

PREDICADOS = ("quantidade_acima", "comprimento_mm_acima", "maior_dimensao_mm_acima", "area_mm2_acima")

# ---------------------------------------------------------------- esquema do YAML


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Regra(_Estrito):
    nota: Nota
    tipos: list[TipoDefeito] = Field(min_length=1)
    zonas: list[Zona] | None = None
    visibilidade: Visibilidade | None = None
    quantidade_acima: int | None = Field(default=None, ge=0)
    comprimento_mm_acima: float | None = Field(default=None, gt=0)
    maior_dimensao_mm_acima: float | None = Field(default=None, gt=0)
    area_mm2_acima: float | None = Field(default=None, gt=0)
    motivo: str
    a_definir: bool = False

    def predicados(self) -> dict[str, float]:
        return {p: getattr(self, p) for p in PREDICADOS if getattr(self, p) is not None}


class GrupoRegras(_Estrito):
    padrao: Nota
    lista: list[Regra]

    @model_validator(mode="after")
    def _ordem(self):
        for a, b in zip(self.lista, self.lista[1:]):
            if ORDEM_NOTA[a.nota] < ORDEM_NOTA[b.nota]:
                raise ValueError(f"regras fora de ordem (da pior para a melhor): '{a.motivo}' antes de '{b.motivo}'")
        for r in self.lista:
            if ORDEM_NOTA[r.nota] < ORDEM_NOTA[self.padrao]:
                raise ValueError(f"regra '{r.motivo}' dá nota melhor que o padrão do grupo")
        return self


class RegraMinima(_Estrito):
    nota: Nota
    tipos: list[TipoDefeito] = Field(min_length=1)
    zonas: list[Zona] | None = None
    visibilidade: Visibilidade | None = None
    motivo: str


class Gerais(_Estrito):
    nota_final: Literal["pior_face"]
    no_minimo: list[RegraMinima] = []


class TratamentoAnomalia(_Estrito):
    tratar_como: TipoDefeito
    exige_revisao: bool = True


class Criterio(_Estrito):
    versao: str
    fonte: str
    notas: list[Nota]
    grupos: dict[str, list[Zona]]
    regras: dict[str, GrupoRegras]
    gerais: Gerais
    anomalia: TratamentoAnomalia

    @model_validator(mode="after")
    def _coerencia(self):
        if self.notas != [Nota.A, Nota.B, Nota.C, Nota.D]:
            raise ValueError("notas deve ser [A, B, C, D]")
        vistas: dict[Zona, str] = {}
        for grupo, zonas in self.grupos.items():
            for z in zonas:
                if z in vistas:
                    raise ValueError(f"zona {z} em dois grupos ({vistas[z]} e {grupo})")
                vistas[z] = grupo
        if faltam := set(Zona) - set(vistas):
            raise ValueError(f"zonas sem grupo: {sorted(faltam)}")
        if set(self.regras) != set(self.grupos):
            raise ValueError("regras e grupos devem ter as mesmas chaves")
        for grupo, g in self.regras.items():
            for r in g.lista:
                if r.zonas and not set(r.zonas) <= set(self.grupos[grupo]):
                    raise ValueError(f"regra '{r.motivo}' usa zona fora do grupo {grupo}")
        if self.anomalia.tratar_como == TipoDefeito.anomalia:
            raise ValueError("anomalia.tratar_como precisa ser um tipo com regras")
        return self

    def grupo_da_zona(self, zona: Zona) -> str:
        return next(g for g, zs in self.grupos.items() if zona in zs)


def carregar(caminho: str | Path) -> Criterio:
    with open(caminho, encoding="utf-8") as f:
        return Criterio.model_validate(yaml.safe_load(f))


@lru_cache
def carregar_versao(versao: str) -> Criterio:
    return carregar(DIR_CRITERIOS / f"{versao}.yaml")


VERSAO_ATUAL = "criterio-v1"

# ---------------------------------------------------------------- entrada e saída


class DefeitoEntrada(BaseModel):
    """Defeito como o motor o vê (proposta da máquina ou marcação do técnico)."""

    model_config = ConfigDict(frozen=True)

    face: Face
    tipo: TipoDefeito
    zona: Zona
    visibilidade: Visibilidade
    estado: EstadoDefeito = EstadoDefeito.proposto
    comprimento_mm: float | None = None
    area_mm2: float | None = None
    maior_dimensao_mm: float | None = None
    confianca: float | None = None
    id: str | None = None


@dataclass
class Margem:
    face: Face
    grupo: str
    motivo: str
    predicado: str
    valor: float
    limite: float
    margem: float


@dataclass
class ResultadoNota:
    versao_criterio: str
    notas_por_face: dict[Face, Nota]
    nota_final: Nota
    justificativas: dict[Face, list[str]]
    pendencias: list[str]
    margens: list[Margem] = field(default_factory=list)

    @property
    def margem_minima(self) -> float | None:
        return min((m.margem for m in self.margens), default=None)

    @property
    def automatizavel(self) -> bool:
        """Sem pendências e longe dos limites (guia 13.3; a parte da confiança de
        trinca fica na automação seletiva)."""
        m = self.margem_minima
        return not self.pendencias and (m is None or m > MARGEM_AUTOMATICO)

    def como_dict(self) -> dict:
        return {
            "versao_criterio": self.versao_criterio,
            "notas_por_face": {str(f): str(n) for f, n in self.notas_por_face.items()},
            "nota_final": str(self.nota_final),
            "justificativas": {str(f): j for f, j in self.justificativas.items()},
            "pendencias": self.pendencias,
            "margens": [m.__dict__ | {"face": str(m.face)} for m in self.margens],
            "margem_minima": self.margem_minima,
            "automatizavel": self.automatizavel,
        }


# ---------------------------------------------------------------- avaliação

_PLURAL = {
    TipoDefeito.risco: ("risco", "riscos"),
    TipoDefeito.trinca: ("trinca", "trincas"),
    TipoDefeito.lascado: ("lascado", "lascados"),
    TipoDefeito.amassado: ("amassado", "amassados"),
    TipoDefeito.descascado: ("descascado", "descascados"),
    TipoDefeito.desgaste: ("desgaste", "desgastes"),
    TipoDefeito.mancha: ("mancha", "manchas"),
    TipoDefeito.anomalia: ("anomalia", "anomalias"),
}
_NOME_GRUPO = {"tela": "Tela", "traseira": "Traseira", "moldura": "Moldura"}
_CAMPO = {
    "comprimento_mm_acima": "comprimento_mm",
    "maior_dimensao_mm_acima": "maior_dimensao_mm",
    "area_mm2_acima": "area_mm2",
}


def _mm(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def _valor(d: DefeitoEntrada, campo: str) -> float | None:
    v = getattr(d, campo)
    if v is None and campo == "maior_dimensao_mm":
        return d.comprimento_mm  # risco é medido pelo comprimento (guia 15.9)
    return v


def _tipo_efetivo(d: DefeitoEntrada, c: Criterio) -> TipoDefeito:
    return c.anomalia.tratar_como if d.tipo == TipoDefeito.anomalia else d.tipo


def _filtrar(defeitos, tipos, zonas, visibilidade, c):
    return [
        d
        for d in defeitos
        if _tipo_efetivo(d, c) in tipos
        and (not zonas or d.zona in zonas)
        and (visibilidade is None or d.visibilidade == visibilidade)
    ]


def _observado(predicado: str, filtrados) -> float | None:
    if predicado == "quantidade_acima":
        return float(len(filtrados))
    vals = [v for v in (_valor(d, _CAMPO[predicado]) for d in filtrados) if v is not None]
    return max(vals) if vals else None


def _casa(regra: Regra, filtrados) -> bool:
    if not filtrados:
        return False
    for p, limite in regra.predicados().items():
        v = _observado(p, filtrados)
        if v is None or not v > limite:
            return False
    return True


def _detalhe(regra: Regra, filtrados) -> str:
    tipos = {d.tipo for d in filtrados}
    n = len(filtrados)
    if len(tipos) == 1:
        sing, plur = _PLURAL[next(iter(tipos))]
        txt = f"{n} {sing if n == 1 else plur}"
    else:
        txt = f"{n} defeitos"
    if regra.visibilidade == Visibilidade.visivel:
        txt += " visíveis" if n > 1 else " visível"
    elif all(d.visibilidade == Visibilidade.so_rasante for d in filtrados):
        txt += " só rasante"
    for campo, rotulo in (("comprimento_mm", "maior"), ("maior_dimensao_mm", "maior"), ("area_mm2", "área máx.")):
        vals = [v for v in (_valor(d, campo) for d in filtrados) if v is not None]
        if vals:
            unidade = "mm²" if campo == "area_mm2" else "mm"
            return f"{txt} ({rotulo} {_mm(max(vals))} {unidade})"
    return txt


def avaliar(
    defeitos: list[DefeitoEntrada],
    criterio: Criterio | None = None,
    faces: list[Face] | None = None,
) -> ResultadoNota:
    c = criterio or carregar_versao(VERSAO_ATUAL)
    faces = faces or list(Face)
    ativos = [d for d in defeitos if d.estado != EstadoDefeito.rejeitado]
    notas: dict[Face, Nota] = {}
    justificativas: dict[Face, list[str]] = {}
    pendencias: list[str] = []
    margens: list[Margem] = []

    if c.anomalia.exige_revisao:
        n_anom = sum(d.tipo == TipoDefeito.anomalia for d in ativos)
        if n_anom:
            pendencias.append(f"{n_anom} região(ões) anômala(s) sem classe: revisão do técnico obrigatória")

    for face in faces:
        da_face = [d for d in ativos if d.face == face]
        nota_face = Nota.A
        textos: list[str] = []
        for grupo, regras in c.regras.items():
            do_grupo = [d for d in da_face if c.grupo_da_zona(d.zona) == grupo]
            if not do_grupo:
                continue
            nota_grupo, decisiva = regras.padrao, None
            for regra in regras.lista:
                filtrados = _filtrar(do_grupo, regra.tipos, regra.zonas, regra.visibilidade, c)
                for p, limite in regra.predicados().items():
                    v = _observado(p, filtrados) if filtrados else None
                    if v is not None:
                        margens.append(Margem(face, grupo, regra.motivo, p, v, limite, abs(v - limite) / limite))
                if decisiva is None and _casa(regra, filtrados):
                    nota_grupo, decisiva = regra.nota, (regra, filtrados)
            if decisiva:
                regra, filtrados = decisiva
                textos.append(f"{_NOME_GRUPO.get(grupo, grupo)}: {regra.motivo} — {_detalhe(regra, filtrados)} → {regra.nota}")
                if regra.a_definir:
                    pendencias.append(f"{face}: regra a definir acionada ({regra.motivo})")
            tratados = {t for r in regras.lista for t in r.tipos}
            for t in sorted({_tipo_efetivo(d, c) for d in do_grupo} - tratados):
                pendencias.append(f"{face}: {t} no grupo {grupo} sem regra no critério")
            nota_face = pior(nota_face, nota_grupo)
        for minima in c.gerais.no_minimo:
            filtrados = _filtrar(da_face, minima.tipos, minima.zonas, minima.visibilidade, c)
            if filtrados and ORDEM_NOTA[minima.nota] > ORDEM_NOTA[nota_face]:
                nota_face = minima.nota
                textos.append(f"Regra geral: {minima.motivo} — {_detalhe(minima, filtrados)} → {minima.nota}")
        notas[face] = nota_face
        justificativas[face] = textos

    return ResultadoNota(
        versao_criterio=c.versao,
        notas_por_face=notas,
        nota_final=pior(*notas.values()) if notas else Nota.A,
        justificativas=justificativas,
        pendencias=pendencias,
        margens=margens,
    )
