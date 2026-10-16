"""Zonas no referencial da face (guia 7.2 e 15.9).

Mapa de rótulos a R px/mm, pintado da menor para a maior prioridade: cada pixel fica com a
zona de maior prioridade que o cobre. Zona de um defeito = a mais frequente sob ele; em
empate, a de maior prioridade.
"""

import numpy as np

# da maior para a menor prioridade (guia 15.9)
PRIORIDADE = ["lente_camera", "ilha_camera", "recorte_tela", "botao", "porta", "quina", "tela", "vidro_traseiro",
              "moldura"]
INTERIOR = {"frente": "tela", "traseira": "vidro_traseiro"}
BORDA_MOLDURA_MM = 0.5


def dims_da_face(face: str, dimensoes_mm: dict) -> tuple[float, float]:
    """(W, H) da face em mm, no referencial 7.2."""
    larg, alt, esp = dimensoes_mm["largura"], dimensoes_mm["altura"], dimensoes_mm["espessura"]
    if face in ("frente", "traseira"):
        return larg, alt
    if face in ("lat_esq", "lat_dir"):
        return esp, alt
    return larg, esp  # topo e base


def mapa(face: str, dimensoes_mm: dict, raio_canto_mm: float, zonas_mm: dict, r: float) -> np.ndarray:
    """Rótulos (índice em PRIORIDADE) do tamanho da face retificada: H×W = altura×R × largura×R."""
    w_mm, h_mm = dims_da_face(face, dimensoes_mm)
    h, w = round(h_mm * r), round(w_mm * r)
    rot = np.full((h, w), PRIORIDADE.index(INTERIOR.get(face, "moldura")), np.int8)

    def pintar(zona, x, y, ww, hh):
        x0, y0 = max(int(round(x * r)), 0), max(int(round(y * r)), 0)
        x1, y1 = min(int(round((x + ww) * r)), w), min(int(round((y + hh) * r)), h)
        if x1 > x0 and y1 > y0:
            alvo = rot[y0:y1, x0:x1]
            i = PRIORIDADE.index(zona)
            alvo[alvo > i] = i  # só sobrescreve zona de prioridade menor

    if face in INTERIOR:  # faixa da borda = moldura
        b = BORDA_MOLDURA_MM * r
        borda = np.zeros((h, w), bool)
        borda[: int(np.ceil(b))], borda[h - int(np.ceil(b)):] = True, True
        borda[:, : int(np.ceil(b))], borda[:, w - int(np.ceil(b)):] = True, True
        rot[borda] = PRIORIDADE.index("moldura")  # atribuição (15.9), não disputa de prioridade
    q = min(raio_canto_mm, w_mm / 2, h_mm / 2)
    for x, y in [(0, 0), (w_mm - q, 0), (0, h_mm - q), (w_mm - q, h_mm - q)]:
        pintar("quina", x, y, q, q)
    for zona, rets in (zonas_mm.get(face) or {}).items():
        for x, y, ww, hh in rets:
            pintar(zona, x, y, ww, hh)
    return rot


def zona_de(rot: np.ndarray, pontos_px: np.ndarray) -> str:
    """Zona sob os pontos (N × 2, x, y em px da face retificada)."""
    h, w = rot.shape
    x = np.clip(np.round(pontos_px[:, 0]).astype(int), 0, w - 1)
    y = np.clip(np.round(pontos_px[:, 1]).astype(int), 0, h - 1)
    contagem = np.bincount(rot[y, x].astype(int), minlength=len(PRIORIDADE))
    maximo = contagem.max()
    return next(PRIORIDADE[i] for i in range(len(PRIORIDADE)) if contagem[i] == maximo)
