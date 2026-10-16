"""Imagens para o painel e o laudo (guia 15.10)."""

import cv2
import numpy as np

from . import config
from .io_imagem import para_u8

# cor fixa por tipo (BGR), a mesma do painel
CORES = {"risco": (60, 200, 255), "trinca": (60, 60, 255), "lascado": (255, 120, 60), "amassado": (255, 60, 200),
         "descascado": (60, 255, 160), "desgaste": (200, 200, 60), "mancha": (160, 160, 160), "anomalia": (255, 255, 255)}


def jpeg(cinza: np.ndarray, qualidade: int = config.JPEG_QUALIDADE_RETIFICADA) -> bytes:
    ok, buf = cv2.imencode(".jpg", para_u8(np.clip(cinza, 0, 1)), [cv2.IMWRITE_JPEG_QUALITY, qualidade])
    if not ok:
        raise ValueError("falha ao codificar JPEG")
    return buf.tobytes()


def anotada(cinza: np.ndarray, deteccoes: list[dict], r: float) -> bytes:
    lo, hi = np.percentile(cinza, [1, 99.7])
    base = cv2.cvtColor(para_u8(np.clip((cinza - lo) / max(hi - lo, 1e-6), 0, 1)), cv2.COLOR_GRAY2BGR)
    esp = max(1, int(r / 10))
    for d in deteccoes:
        cor = CORES.get(d["tipo"], (255, 255, 255))
        g = d.get("geometria_mm") or {}
        if g.get("pontos"):
            pts = np.round(np.array(g["pontos"]) * r).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(base, [pts], g.get("tipo") == "poligono", cor, esp, cv2.LINE_AA)
        x, y, w, h = (np.array(d["caixa_mm"]) * r).astype(int)
        cv2.rectangle(base, (x - 2, y - 2), (x + w + 2, y + h + 2), cor, 1)
        medida = d.get("comprimento_mm") or d.get("maior_dimensao_mm")
        if medida:
            cv2.putText(base, f"{medida:.1f} mm".replace(".", ","), (x, max(y - 4, 10)), cv2.FONT_HERSHEY_SIMPLEX,
                        max(r / 40, 0.4), cor, 1, cv2.LINE_AA)
    ok, buf = cv2.imencode(".jpg", base, [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALIDADE_RETIFICADA])
    return buf.tobytes()
