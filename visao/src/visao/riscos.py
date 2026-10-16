"""Camada (a): riscos na luz rasante (guia 15.4).

Na luz rasante, risco é uma linha fina e clara sobre fundo escuro. Subtrair a foto
`ambiente` tira os reflexos fixos; o top-hat tira o fundo; o limiar robusto
(mediana + k × MAD) separa as linhas; o esqueleto mede o comprimento.
"""

from collections import deque
from dataclasses import dataclass, field

import cv2
import numpy as np
from skimage.morphology import skeletonize

from .config import PARAM_RISCOS, ParamRiscos

_VIZINHOS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass
class Risco:
    comprimento_mm: float
    largura_mm: float  # aparente; não usar no critério (microrriscos espalham luz)
    angulo_graus: float  # 0 = horizontal na imagem, 0 a 180
    contraste: float  # resposta média no esqueleto, em MADs acima da mediana
    caixa_px: tuple[int, int, int, int]  # x, y, w, h na imagem inteira
    caminho_px: np.ndarray  # N × 2 (x, y), amostrado, na imagem inteira
    esqueleto_px: np.ndarray = field(repr=False)  # M × 2 (x, y), todos os pixels


def _recorte(mascara: np.ndarray, margem: int):
    ys, xs = np.nonzero(mascara)
    if len(ys) == 0:
        raise ValueError("Máscara vazia")
    h, w = mascara.shape
    return (
        max(ys.min() - margem, 0),
        min(ys.max() + 1 + margem, h),
        max(xs.min() - margem, 0),
        min(xs.max() + 1 + margem, w),
    )


def realcar(rasante, ambiente, mascara, px_mm, largura_max_mm=PARAM_RISCOS.largura_max_mm):
    """Top-hat de (rasante − ambiente). `ambiente=None` realça a própria imagem."""
    d = rasante.astype(np.float32)
    if ambiente is not None:
        d = d - ambiente.astype(np.float32)  # sem np.clip: o top-hat já tira o fundo
    k = int(round(largura_max_mm * px_mm * 4)) | 1
    el = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    th = cv2.morphologyEx(d, cv2.MORPH_TOPHAT, el)
    th[~mascara] = 0
    return th


# Piso do MAD: meio nível de 8 bits. Vidro preto liso com compressão forte pode dar MAD ≈ 0;
# sem piso, o limiar vira zero e o ruído de compressão liga tudo numa teia (some risco real).
MAD_MINIMO = 0.5 / 255


def estatistica(th, mascara):
    v = th[mascara]
    med = float(np.median(v))
    mad = max(float(np.median(np.abs(v - med)) * 1.4826), MAD_MINIMO)
    return med, mad


def binarizar(th, mascara, k_mad=PARAM_RISCOS.k_mad):
    med, mad = estatistica(th, mascara)
    return (th > med + k_mad * mad) & mascara


def caminho_mais_longo(esq: np.ndarray) -> np.ndarray:
    """Caminho (y, x) entre as duas pontas mais distantes do esqueleto."""
    ys, xs = np.nonzero(esq)
    if len(ys) < 2:
        return np.stack([ys, xs], axis=1)
    pixels = set(zip(ys.tolist(), xs.tolist()))

    def mais_distante(origem):
        pai = {origem: None}
        fila = deque([origem])
        ultimo = origem
        while fila:
            p = fila.popleft()
            ultimo = p
            for dy, dx in _VIZINHOS:
                q = (p[0] + dy, p[1] + dx)
                if q in pixels and q not in pai:
                    pai[q] = p
                    fila.append(q)
        return ultimo, pai

    ponta, _ = mais_distante(next(iter(pixels)))  # duas buscas: as duas pontas mais distantes
    outra, pai = mais_distante(ponta)
    caminho = []
    while outra is not None:
        caminho.append(outra)
        outra = pai[outra]
    return np.array(caminho)


def amostrar(caminho: np.ndarray, passo: int = 5) -> np.ndarray:
    if len(caminho) < 2:
        return caminho.astype(float)
    amostra = list(caminho[::passo])
    if (len(caminho) - 1) % passo:
        amostra.append(caminho[-1])
    return np.array(amostra, dtype=float)


def comprimento_esqueleto(esq, passo=5):
    """Comprimento (px) do caminho mais longo, medido numa polilinha amostrada a cada
    `passo` pixels. Somar passos de 1 e √2 superestima ~5% (até 8% a 22,5°)."""
    pts = amostrar(caminho_mais_longo(esq), passo)
    if len(pts) < 2:
        return 0.0
    return float(np.sum(np.hypot(*np.diff(pts, axis=0).T)))


def riscos(binario, th, mascara, px_mm, p: ParamRiscos = PARAM_RISCOS, deslocamento=(0, 0)) -> list[Risco]:
    """Componentes alongados de `binario`. `deslocamento` = (y0, x0) do recorte."""
    med, mad = estatistica(th, mascara)
    r = int(round(p.emenda_mm * px_mm)) | 1
    b = cv2.morphologyEx(
        binario.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))
    )
    b &= mascara.astype(np.uint8)  # o fechamento não pode vazar para fora da zona avaliada
    n, rot, stats, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    y_off, x_off = deslocamento
    achados = []
    comp_min_px = p.comp_min_mm * px_mm
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if np.hypot(w, h) < comp_min_px:
            continue
        esq = skeletonize(rot[y : y + h, x : x + w] == i)
        caminho = caminho_mais_longo(esq)
        pts = amostrar(caminho)
        if len(pts) < 2:
            continue
        comp_px = float(np.sum(np.hypot(*np.diff(pts, axis=0).T)))
        comp_mm = comp_px / px_mm
        if comp_mm < p.comp_min_mm:
            continue
        n_esq = max(int(esq.sum()), 1)
        largura_px = area / n_esq
        if comp_px / max(largura_px, 1e-6) < p.alongamento_min:
            continue  # ponto ou poeira
        ey, ex = np.nonzero(esq)
        resposta = th[ey + y, ex + x]
        cy, cx = ey - ey.mean(), ex - ex.mean()
        ang = float(np.degrees(0.5 * np.arctan2(2 * np.sum(cx * cy), np.sum(cx * cx) - np.sum(cy * cy))) % 180)
        achados.append(
            Risco(
                comprimento_mm=round(comp_mm, 2),
                largura_mm=round(largura_px / px_mm, 3),
                angulo_graus=round(ang, 1),
                contraste=round(float((resposta.mean() - med) / mad), 2),
                caixa_px=(int(x + x_off), int(y + y_off), int(w), int(h)),
                caminho_px=np.stack([pts[:, 1] + x + x_off, pts[:, 0] + y + y_off], axis=1),
                esqueleto_px=np.stack([ex + x + x_off, ey + y + y_off], axis=1),
            )
        )
    return achados


@dataclass
class Deteccao:
    riscos: list[Risco]
    binario: np.ndarray  # no recorte
    th: np.ndarray  # no recorte
    recorte: tuple[int, int, int, int]  # y0, y1, x0, x1


def detectar(rasante, ambiente, mascara, px_mm, p: ParamRiscos = PARAM_RISCOS) -> Deteccao:
    """Pipeline completo da camada (a) numa imagem, restrito à máscara."""
    margem = int(p.largura_max_mm * px_mm * 4) + 2
    y0, y1, x0, x1 = _recorte(mascara, margem)
    m = mascara[y0:y1, x0:x1]
    amb = ambiente[y0:y1, x0:x1] if ambiente is not None else None
    th = realcar(rasante[y0:y1, x0:x1], amb, m, px_mm, p.largura_max_mm)
    b = binarizar(th, m, p.k_mad)
    return Deteccao(riscos(b, th, m, px_mm, p, deslocamento=(y0, x0)), b, th, (y0, y1, x0, x1))


def detectar_binario(binario, th, mascara, px_mm, recorte, p: ParamRiscos = PARAM_RISCOS) -> list[Risco]:
    """Riscos a partir de um binário já pronto (ex.: união de rasante_a e rasante_b)."""
    y0, y1, x0, x1 = recorte
    return riscos(binario, th, mascara[y0:y1, x0:x1], px_mm, p, deslocamento=(y0, x0))


@dataclass
class Realce:
    """Outra imagem realçada no mesmo recorte, para medir contraste de riscos já achados."""

    th_dilatado: np.ndarray
    mediana: float
    mad: float
    recorte: tuple[int, int, int, int]

    @classmethod
    def de(cls, img, mascara, px_mm, recorte, p: ParamRiscos = PARAM_RISCOS):
        y0, y1, x0, x1 = recorte
        m = mascara[y0:y1, x0:x1]
        th = realcar(img[y0:y1, x0:x1], None, m, px_mm, p.largura_max_mm)
        med, mad = estatistica(th, m)
        return cls(cv2.dilate(th, np.ones((3, 3), np.uint8)), med, mad, recorte)

    def contraste(self, risco: Risco) -> float:
        """Contraste (em MADs) ao longo do esqueleto do risco (dilatado 1 px). Na foto
        `ambiente`, é a base de `visivel` × `so_rasante` (guia 15.5)."""
        y0, _, x0, _ = self.recorte
        v = self.th_dilatado[risco.esqueleto_px[:, 1] - y0, risco.esqueleto_px[:, 0] - x0]
        return round(float((v.mean() - self.mediana) / self.mad), 2)
