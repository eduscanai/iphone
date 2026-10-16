"""Fusão por face (guia 15.8): junta as detecções da mesma face em todas as fotos.

Mesmo defeito se:
- riscos: distância de Hausdorff entre as polilinhas ≤ 1 mm, ou ≥ 50% do mais curto a até
  1 mm do outro;
- demais: IoU das caixas ≥ 0,3, ou o centro de uma dentro da outra.
Defeito fundido: geometria da detecção de maior contraste; comprimento = o maior;
tipo por prioridade detector > OpenCV > PatchCore; confiança = a maior.
"""

import time

import numpy as np

from . import config

PRIORIDADE_FONTE = {"detector": 0, "opencv_riscos": 1, "patchcore": 2}


def _densificar(pontos, passo_mm=0.25) -> np.ndarray:
    p = np.asarray(pontos, float)
    if len(p) < 2:
        return p
    out = [p[0]]
    for a, b in zip(p[:-1], p[1:]):
        n = max(int(np.ceil(np.linalg.norm(b - a) / passo_mm)), 1)
        out.extend(a + (b - a) * (np.arange(1, n + 1) / n)[:, None])
    return np.array(out)


def _dist_min(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Para cada ponto de a, a distância ao ponto mais próximo de b."""
    return np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(-1)).min(axis=1)


def mesmo_risco(a: dict, b: dict) -> bool:
    pa = _densificar(a["geometria_mm"]["pontos"])
    pb = _densificar(b["geometria_mm"]["pontos"])
    if len(pa) == 0 or len(pb) == 0:
        return False
    da, db = _dist_min(pa, pb), _dist_min(pb, pa)
    if max(da.max(), db.max()) <= config.FUSAO_HAUSDORFF_MM:
        return True
    curto = da if len(pa) <= len(pb) else db
    return float(np.mean(curto <= config.FUSAO_HAUSDORFF_MM)) >= config.FUSAO_SOBREPOSICAO_MIN


def _iou(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    uniao = aw * ah + bw * bh - inter
    return inter / uniao if uniao > 0 else 0.0


def _centro_dentro(a, b) -> bool:
    cx, cy = a[0] + a[2] / 2, a[1] + a[3] / 2
    return b[0] <= cx <= b[0] + b[2] and b[1] <= cy <= b[1] + b[3]


def mesmo_defeito(a: dict, b: dict) -> bool:
    if a["face"] != b["face"]:
        return False
    if a["tipo"] == b["tipo"] == "risco" and a.get("geometria_mm") and b.get("geometria_mm"):
        return mesmo_risco(a, b)
    ca, cb = a["caixa_mm"], b["caixa_mm"]
    return _iou(ca, cb) >= config.FUSAO_IOU_MIN or _centro_dentro(ca, cb) or _centro_dentro(cb, ca)


def _grupos(deteccoes: list[dict]) -> list[list[dict]]:
    pai = list(range(len(deteccoes)))

    def raiz(i):
        while pai[i] != i:
            pai[i] = pai[pai[i]]
            i = pai[i]
        return i

    for i in range(len(deteccoes)):
        for j in range(i + 1, len(deteccoes)):
            if mesmo_defeito(deteccoes[i], deteccoes[j]):
                pai[raiz(i)] = raiz(j)
    grupos: dict[int, list[dict]] = {}
    for i, d in enumerate(deteccoes):
        grupos.setdefault(raiz(i), []).append(d)
    return list(grupos.values())


def fundir_grupo(g: list[dict]) -> dict:
    principal = max(g, key=lambda d: (d.get("contraste_rasante") or 0, d.get("confianca") or 0))
    por_tipo = min(g, key=lambda d: PRIORIDADE_FONTE.get(d["fonte"], 9))
    tipo = por_tipo["tipo"]
    comprimentos = [d["comprimento_mm"] for d in g if d.get("comprimento_mm") is not None]
    areas = [d["area_mm2"] for d in g if d.get("area_mm2") is not None]
    maiores = [d["maior_dimensao_mm"] for d in g if d.get("maior_dimensao_mm") is not None]
    c_amb = [d["contraste_ambiente"] for d in g if d.get("contraste_ambiente") is not None]
    if tipo == "risco":
        visibilidade = "visivel" if c_amb and max(c_amb) >= config.T_VISIVEL else "so_rasante"
    else:
        visibilidade = next((d["visibilidade"] for d in g if d.get("visibilidade")), "visivel")
    comp = max(comprimentos) if comprimentos else None
    return {
        "face": principal["face"], "tipo": tipo, "zona": principal["zona"], "visibilidade": visibilidade,
        "foto_principal": principal.get("foto_id"), "fotos": sorted({d["foto_id"] for d in g if d.get("foto_id")}),
        "caixa_mm": principal["caixa_mm"], "geometria_mm": principal.get("geometria_mm"),
        "comprimento_mm": comp, "area_mm2": max(areas) if areas else None,
        "maior_dimensao_mm": max(maiores) if maiores else comp,
        "confianca": max((d.get("confianca") or 0 for d in g), default=None), "fonte": por_tipo["fonte"],
    }


def fundir_sessao(t: dict, modelos: dict | None = None) -> dict:
    """Tarefa `fusao` → resultado (7.9)."""
    t0 = time.monotonic()
    deteccoes, cobertas = [], set()
    for f in t["fotos"]:
        r = f.get("resultado")
        if not r or not r.get("qualidade", {}).get("ok"):
            continue
        for fe in r.get("faces_extraidas", []):
            cobertas.add(fe["face"])
        for d in r.get("deteccoes", []):
            deteccoes.append(d | {"foto_id": f["foto_id"]})
    faces_roteiro = sorted({face for p in t["roteiro"]["passos"] for face in p["faces"]})
    defeitos = [fundir_grupo(g) for g in _grupos(deteccoes)]
    defeitos.sort(key=lambda d: (d["face"], d["caixa_mm"][1], d["caixa_mm"][0]))
    return {
        "tarefa_id": t["tarefa_id"], "tipo": "fusao", "sessao_id": t["sessao_id"],
        "versao_visao": config.VERSAO_PIPELINE, "modelos": modelos or {},
        "defeitos": defeitos, "faces_sem_foto_valida": [f for f in faces_roteiro if f not in cobertas],
        "tempo_ms": int((time.monotonic() - t0) * 1000),
    }
