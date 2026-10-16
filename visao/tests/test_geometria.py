import cv2
import numpy as np
import pytest

from visao import geometria
from sinteticos import retangulo_arredondado

LARG, ALT, RAIO = 71.5, 146.7, 9.0
PX_MM = 10.0


def _cena(h_mm_para_px, forma=(2400, 3200), fundo=0.08, aparelho=0.18, semente=0):
    """Aparelho escuro sobre fundo escuro, com borda de alumínio mais clara."""
    m = retangulo_arredondado(LARG, ALT, RAIO, PX_MM).astype(np.float32)
    dentro = cv2.erode((m > 0.5).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(np.float32)
    face = fundo * (1 - m) + aparelho * m + 0.15 * (m - dentro).clip(0, 1)
    h = h_mm_para_px @ np.diag([1 / PX_MM, 1 / PX_MM, 1])
    img = cv2.warpPerspective(face, h, (forma[1], forma[0]), flags=cv2.INTER_LINEAR, borderValue=fundo)
    rng = np.random.default_rng(semente)
    return (img + rng.normal(0, 0.004, img.shape)).astype(np.float32)


def _homografia(semente, perspectiva=True):
    rng = np.random.default_rng(semente)
    ang = rng.uniform(-np.pi, np.pi)
    s = rng.uniform(12, 14)  # px/mm; o aparelho cabe no quadro em qualquer ângulo
    c, si = np.cos(ang) * s, np.sin(ang) * s
    h = np.array([[c, -si, 1600], [si, c, 1200], [0, 0, 1]], float)
    h = h @ np.array([[1, 0, -LARG / 2], [0, 1, -ALT / 2], [0, 0, 1]])
    if perspectiva:
        # câmera inclinada ~1°: a escala varia ~±1,5% de um lado ao outro do aparelho
        a, b = rng.uniform(-1e-5, 1e-5, 2)
        centro = np.array([[1, 0, 1600], [0, 1, 1200], [0, 0, 1]], float)
        p = np.array([[1, 0, 0], [0, 1, 0], [a, b, 1]], float)
        h = centro @ p @ np.linalg.inv(centro) @ h
    return h, s


def _cantos_reais(h):
    mm = np.array([[0, 0], [LARG, 0], [LARG, ALT], [0, ALT]], float).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(mm, h).reshape(-1, 2)


@pytest.mark.parametrize("semente", range(5))
def test_cantos(semente):
    h, s = _homografia(semente)
    img = _cena(h)
    ap = geometria.encontrar_aparelho(img, (LARG, ALT))
    assert ap is not None and not ap.fora_do_quadro
    reais = _cantos_reais(h)
    erros = [np.min(np.linalg.norm(reais - c, axis=1)) for c in ap.cantos]
    assert max(erros) / s < 0.2


@pytest.mark.parametrize("semente", range(5))
def test_escala(semente):
    h, s = _homografia(semente, perspectiva=False)
    ap = geometria.encontrar_aparelho(_cena(h), (LARG, ALT))
    assert ap is not None
    assert ap.px_por_mm == pytest.approx(s, rel=0.005)
    assert ap.residuo_bordas_mm < 0.1


def test_ordenar_cantos_lado_curto_primeiro():
    c = np.array([[0, 0], [0, 200], [100, 200], [100, 0]], float)
    o = geometria.ordenar_cantos(c)
    assert np.linalg.norm(o[1] - o[0]) == pytest.approx(100)
    assert o[0].tolist() == [0, 0]


def test_aruco_escala():
    dic = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    img = np.full((1000, 1000), 255, np.uint8)
    lado_px = 300  # 30 mm a 10 px/mm
    img[100:400, 100:400] = cv2.aruco.generateImageMarker(dic, 0, lado_px)
    marcadores = geometria.detectar_aruco(img.astype(np.float32) / 255)
    assert [m.id for m in marcadores] == [0]
    assert geometria.px_por_mm_aruco(marcadores) == pytest.approx(10.0, rel=0.01)


def test_retificar_e_mascara():
    h, s = _homografia(0, perspectiva=False)
    img = _cena(h)
    ap = geometria.encontrar_aparelho(img, (LARG, ALT))
    ret = geometria.retificar(img, ap.cantos, (LARG, ALT), 20)
    assert ret.shape == (round(ALT * 20), round(LARG * 20))
    m = geometria.mascara_face(img.shape, ap.cantos, (LARG, ALT), borda_mm=0.5, px_mm=s)
    area_mm2 = m.sum() / s**2
    esperado = (LARG - 1) * (ALT - 1) - (4 - np.pi) * (RAIO - 0.5) ** 2
    assert area_mm2 == pytest.approx(esperado, rel=0.01)


def test_fora_do_quadro():
    h = np.array([[15, 0, 400], [0, 15, -300], [0, 0, 1]], float)  # topo cortado
    ap = geometria.encontrar_aparelho(_cena(h), (LARG, ALT))
    assert ap is None or ap.fora_do_quadro
