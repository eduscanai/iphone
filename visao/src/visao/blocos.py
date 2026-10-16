"""Blocos (tiles) da face retificada e supressão de não máximos em mm (guia 15.6 e 15.7).
Defeitos são pequenos demais para a imagem inteira reduzida: o detector e o PatchCore rodam
em blocos com sobreposição, e as detecções voltam para o referencial da face em mm."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Bloco:
    x: int
    y: int
    w: int
    h: int


def blocos(altura: int, largura: int, lado: int, sobreposicao: float) -> list[Bloco]:
    """Cobre a imagem inteira; o último bloco de cada eixo encosta na borda."""
    passo = max(1, int(round(lado * (1 - sobreposicao))))

    def eixo(n):
        if n <= lado:
            return [0]
        pos = list(range(0, n - lado + 1, passo))
        if pos[-1] != n - lado:
            pos.append(n - lado)
        return pos

    return [Bloco(x, y, min(lado, largura), min(lado, altura)) for y in eixo(altura) for x in eixo(largura)]


def iou(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    uniao = aw * ah + bw * bh - inter
    return inter / uniao if uniao > 0 else 0.0


def nms_mm(deteccoes: list[dict], limiar_iou: float = 0.5) -> list[dict]:
    """Supressão de não máximos por tipo, com caixas em mm (`caixa_mm` = x, y, w, h)."""
    saida = []
    for tipo in sorted({d["tipo"] for d in deteccoes}):
        candidatos = sorted((d for d in deteccoes if d["tipo"] == tipo), key=lambda d: -d["confianca"])
        mantidos: list[dict] = []
        for d in candidatos:
            if all(iou(d["caixa_mm"], m["caixa_mm"]) < limiar_iou for m in mantidos):
                mantidos.append(d)
        saida.extend(mantidos)
    return saida


def caixa_bloco_para_mm(caixa_px, bloco: Bloco, r: float) -> list[float]:
    """Caixa (x0, y0, x1, y1) em px do bloco → [x, y, w, h] em mm da face."""
    x0, y0, x1, y1 = caixa_px
    return [round((bloco.x + x0) / r, 2), round((bloco.y + y0) / r, 2), round((x1 - x0) / r, 2), round((y1 - y0) / r, 2)]


def mapa_maximo(altura: int, largura: int, mapas: list[tuple[Bloco, np.ndarray]]) -> np.ndarray:
    """Junta mapas de anomalia por bloco (máximo onde há sobreposição)."""
    out = np.zeros((altura, largura), np.float32)
    for b, m in mapas:
        out[b.y:b.y + b.h, b.x:b.x + b.w] = np.maximum(out[b.y:b.y + b.h, b.x:b.x + b.w], m[: b.h, : b.w])
    return out
