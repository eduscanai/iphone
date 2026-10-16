"""Concordância máquina × técnico (guia 11.3 e 13.1).

Por padrão só sessões cegas: quem vê a sugestão tende a confirmá-la (R11). Verdade =
nota do técnico (última avaliação humana, não substituída). Máquina = sugestão.
"""

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..base.modelos import Sessao
from .enums import Face, OrigemNota
from .modelos import AvaliacaoEstetica, SessaoEstetica, SugestaoEstetica

NOTAS = ["A", "B", "C", "D"]
IDX = {n: i for i, n in enumerate(NOTAS)}


@dataclass
class Par:
    sessao_id: str
    maquina: str
    tecnico: str
    maquina_faces: dict
    tecnico_faces: dict
    quando: datetime
    modelo: str | None
    tecnico_id: str | None
    cega: bool
    conjunto: str


def kappa_quadratico(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    k = len(NOTAS)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[IDX[x]][IDX[y]] += 1 / n
    lin = [sum(obs[i]) for i in range(k)]
    col = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    num = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * lin[i] * col[j] for i in range(k) for j in range(k))
    return None if den == 0 else 1 - num / den


def metricas(maquina: list[str], tecnico: list[str], bootstrap: int = 1000) -> dict:
    n = len(maquina)
    if n == 0:
        return {"n": 0}
    dif = [abs(IDX[a] - IDX[b]) for a, b in zip(maquina, tecnico)]
    matriz = [[0] * 4 for _ in range(4)]  # linha = técnico, coluna = máquina
    for a, b in zip(maquina, tecnico):
        matriz[IDX[b]][IDX[a]] += 1
    recall = {}
    for nota in NOTAS:
        total = sum(matriz[IDX[nota]])
        recall[nota] = matriz[IDX[nota]][IDX[nota]] / total if total else None
    kappa = kappa_quadratico(maquina, tecnico)
    ic = None
    if bootstrap and n >= 10 and kappa is not None:
        rng = random.Random(0)  # determinístico
        amostras = []
        for _ in range(bootstrap):
            idx = [rng.randrange(n) for _ in range(n)]
            k = kappa_quadratico([maquina[i] for i in idx], [tecnico[i] for i in idx])
            if k is not None:
                amostras.append(k)
        amostras.sort()
        if amostras:
            ic = [amostras[int(0.025 * len(amostras))], amostras[int(0.975 * len(amostras)) - 1]]
    return {
        "n": n,
        "exata": sum(d == 0 for d in dif) / n,
        "mais_menos_1": sum(d <= 1 for d in dif) / n,
        "a_2_ou_mais": sum(d >= 2 for d in dif),
        "kappa_quadratico": kappa,
        "kappa_ic95": ic,
        "recall": recall,
        "matriz": {"linhas": "técnico", "colunas": "máquina", "notas": NOTAS, "valores": matriz},
        "limite_superior_erro_2_notas": 3 / n,  # regra de três: 0 em n → taxa < 3/n (95%)
    }


def pares(db: Session, loja_id=None, de=None, ate=None, modelo=None, tecnico_id=None, incluir_nao_cegas=False,
          so_teste=False, limite: int | None = None) -> list[Par]:
    """Última avaliação humana de cada sessão (não automática, não substituída) × sugestão usada."""
    substituidas = select(AvaliacaoEstetica.substitui_id).where(AvaliacaoEstetica.substitui_id.is_not(None))
    q = (
        select(AvaliacaoEstetica, SugestaoEstetica, Sessao, SessaoEstetica)
        .join(SugestaoEstetica, SugestaoEstetica.id == AvaliacaoEstetica.sugestao_id)
        .join(Sessao, Sessao.id == AvaliacaoEstetica.sessao_id)
        .join(SessaoEstetica, SessaoEstetica.sessao_id == AvaliacaoEstetica.sessao_id)
        .where(AvaliacaoEstetica.origem != OrigemNota.automatica, AvaliacaoEstetica.id.not_in(substituidas))
        .order_by(AvaliacaoEstetica.criada_em.desc())
    )
    if loja_id:
        q = q.where(Sessao.loja_id == loja_id)
    if de:
        q = q.where(AvaliacaoEstetica.criada_em >= de)
    if ate:
        q = q.where(AvaliacaoEstetica.criada_em < ate)
    if modelo:
        q = q.where(Sessao.identificador_modelo == modelo)
    if tecnico_id:
        q = q.where(AvaliacaoEstetica.tecnico_id == tecnico_id)
    if not incluir_nao_cegas:
        q = q.where(AvaliacaoEstetica.cega.is_(True))
    if so_teste:
        q = q.where(SessaoEstetica.conjunto == "teste")
    vistos, out = set(), []
    for av, sug, s, se in db.execute(q):
        if av.sessao_id in vistos:  # mais de uma avaliação sem substituição: vale a mais recente
            continue
        vistos.add(av.sessao_id)
        out.append(Par(str(av.sessao_id), sug.nota_final, av.nota_final, sug.notas_por_face, av.notas_por_face,
                       av.criada_em, s.identificador_modelo, str(av.tecnico_id) if av.tecnico_id else None,
                       av.cega, se.conjunto))
        if limite and len(out) >= limite:
            break
    return out


def relatorio(lista: list[Par], face: str | None = None) -> dict:
    if face:
        a = [p.maquina_faces.get(face) for p in lista]
        b = [p.tecnico_faces.get(face) for p in lista]
        ok = [(x, y) for x, y in zip(a, b) if x and y]
        geral = metricas([x for x, _ in ok], [y for _, y in ok])
    else:
        geral = metricas([p.maquina for p in lista], [p.tecnico for p in lista])
    por_face = {f.value: metricas([p.maquina_faces.get(f.value, "A") for p in lista],
                                  [p.tecnico_faces.get(f.value, "A") for p in lista], bootstrap=0) for f in Face}
    semanas = defaultdict(list)
    for p in lista:
        ano, sem, _ = p.quando.isocalendar()
        semanas[f"{ano}-S{sem:02d}"].append(p)
    evolucao = [{"semana": k, "n": len(v), "exata": sum(x.maquina == x.tecnico for x in v) / len(v)}
                for k, v in sorted(semanas.items())]
    discordantes = [{"sessao_id": p.sessao_id, "maquina": p.maquina, "tecnico": p.tecnico, "modelo": p.modelo,
                     "distancia": abs(IDX[p.maquina] - IDX[p.tecnico])}
                    for p in lista if p.maquina != p.tecnico]
    discordantes.sort(key=lambda d: -d["distancia"])
    return {"geral": geral, "por_face": por_face, "evolucao_semanal": evolucao, "discordantes": discordantes[:200]}
