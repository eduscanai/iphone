"""Camada (b): PatchCore por família de acabamento, na traseira e na moldura (guia R7 e 15.6).
Regiões acima do limiar viram defeitos `anomalia`, sempre revisados pelo técnico (R22)."""

import cv2
import numpy as np

from . import blocos as bl
from . import zonas
from .modelos import Modelos

LADO_BLOCO = 256
SOBREPOSICAO = 64 / 256
AREA_MIN_MM2 = 0.5


def familia_da_face(face: str, familia: dict) -> str | None:
    if face == "traseira":
        return f"traseira-{familia.get('traseira')}" if familia.get("traseira") else None
    if face in ("lat_esq", "lat_dir", "topo", "base"):
        return f"borda-{familia.get('moldura')}" if familia.get("moldura") else None
    return None  # tela: camadas (a) e (c)


def detectar(modelos: Modelos, face: str, familia: dict, ret: np.ndarray, rot: np.ndarray, r: float):
    """Devolve (defeitos `anomalia`, mapa de anomalia 0–1 ou None)."""
    chave = familia_da_face(face, familia)
    if chave is None or chave not in modelos.patchcore or "desconhecido" in chave:
        return [], None
    import torch

    modelo, limiar = modelos.patchcore[chave]
    excluir = rot == zonas.PRIORIDADE.index("lente_camera")  # reflexos fortes
    mapas = []
    for b in bl.blocos(*ret.shape, LADO_BLOCO, SOBREPOSICAO):
        bloco = np.clip(ret[b.y:b.y + b.h, b.x:b.x + b.w], 0, 1)
        x = torch.from_numpy(np.repeat(bloco[None, None], 3, axis=1)).float()
        with torch.no_grad():
            saida = modelo(x)  # VERIFICAR o formato de saída na versão do anomalib
        mapa = saida.anomaly_map.squeeze().cpu().numpy()
        mapas.append((b, cv2.resize(mapa, (b.w, b.h))))
    mapa = bl.mapa_maximo(*ret.shape, mapas)
    mapa[excluir] = 0
    binario = (mapa > limiar).astype(np.uint8)
    n, rotulos, stats, _ = cv2.connectedComponentsWithStats(binario)
    achados = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area / r**2 < AREA_MIN_MM2:
            continue
        ys, xs = np.nonzero(rotulos == i)
        pts = np.stack([xs, ys], axis=1).astype(np.float32)
        (_, _), (rw, rh), _ = cv2.minAreaRect(pts)
        achados.append({"face": face, "fonte": "patchcore", "tipo": "anomalia", "zona": zonas.zona_de(rot, pts),
                        "caixa_mm": [round(x / r, 2), round(y / r, 2), round(w / r, 2), round(h / r, 2)],
                        "area_mm2": round(area / r**2, 2), "maior_dimensao_mm": round(max(rw, rh) / r, 2),
                        "confianca": round(float(np.clip(mapa[ys, xs].max(), 0, 1)), 3), "visibilidade": "visivel"})
    return achados, np.clip(mapa / max(limiar * 2, 1e-6), 0, 1)
