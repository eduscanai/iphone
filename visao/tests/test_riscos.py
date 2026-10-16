import cv2
import numpy as np
import pytest

from visao import riscos
from sinteticos import desenhar_linha, desenhar_poeira, fundo

PX_MM = 20.0
LINHAS = [  # (p0_mm, p1_mm)
    ((10, 10), (12, 10)),  # 2 mm, horizontal
    ((10, 20), (13, 24)),  # 5 mm, inclinada
    ((30, 15), (30, 25)),  # 10 mm, vertical
    ((8, 40), (8 + 20 * np.cos(0.3927), 40 + 20 * np.sin(0.3927))),  # 20 mm a 22,5°
    ((25, 70), (45, 90)),  # 28,3 mm a 45°
]


def _cena(com_poeira=False):
    amb = fundo(110, 60, PX_MM)
    ras = amb.copy() + np.random.default_rng(5).normal(0, 0.004, amb.shape).astype(np.float32)
    for p0, p1 in LINHAS:
        desenhar_linha(ras, p0, p1, PX_MM)
    poeira = desenhar_poeira(ras, 200, PX_MM) if com_poeira else []
    return amb, ras, poeira


def _mais_perto(achados, p0, p1):
    centro = (np.array(p0) + np.array(p1)) / 2 * PX_MM
    return min(achados, key=lambda r: np.linalg.norm(r.caminho_px.mean(axis=0) - centro))


@pytest.mark.parametrize("p0,p1", LINHAS)
def test_comprimento(p0, p1):
    amb, ras, _ = _cena()
    mascara = np.ones(amb.shape, bool)
    achados = riscos.detectar(ras, amb, mascara, PX_MM).riscos
    real = float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))
    medido = _mais_perto(achados, p0, p1).comprimento_mm
    assert abs(medido - real) <= max(0.05 * real, 0.5), (real, medido)


def test_numero_de_riscos_sem_falsos_positivos():
    amb, ras, _ = _cena()
    achados = riscos.detectar(ras, amb, np.ones(amb.shape, bool), PX_MM).riscos
    assert len(achados) == len(LINHAS)


def test_poeira_rejeitada():
    amb, ras, poeira = _cena(com_poeira=True)
    achados = riscos.detectar(ras, amb, np.ones(amb.shape, bool), PX_MM).riscos
    pontos = np.concatenate([r.esqueleto_px for r in achados])
    aceitos = sum(np.min(np.hypot(*(pontos - np.array(p)).T)) < 4 for p in poeira)
    # a poeira que cai em cima de uma linha sintética não conta como falso positivo
    sobre_linha = 0
    for p in poeira:
        for p0, p1 in LINHAS:
            a, b, q = np.array(p0) * PX_MM, np.array(p1) * PX_MM, np.array(p)
            t = np.clip(np.dot(q - a, b - a) / np.dot(b - a, b - a), 0, 1)
            if np.linalg.norm(q - (a + t * (b - a))) < 0.5 * PX_MM * 2:
                sobre_linha += 1
                break
    assert aceitos - sobre_linha <= 0.05 * len(poeira)


def test_comprimento_esqueleto_diagonal():
    esq = np.eye(101, dtype=bool)
    assert riscos.comprimento_esqueleto(esq) == pytest.approx(100 * np.sqrt(2), rel=1e-6)


def test_deterministico():
    amb, ras, _ = _cena(com_poeira=True)
    m = np.ones(amb.shape, bool)
    a = [(r.comprimento_mm, r.caixa_px) for r in riscos.detectar(ras, amb, m, PX_MM).riscos]
    b = [(r.comprimento_mm, r.caixa_px) for r in riscos.detectar(ras, amb, m, PX_MM).riscos]
    assert a == b


def test_fundo_perfeitamente_liso():
    """Vidro preto liso + compressão: MAD ≈ 0. Sem piso no MAD, o ruído liga tudo e risco some."""
    amb = np.full((2200, 1200), 0.06, np.float32)
    ras = amb.copy()
    for p0, p1 in LINHAS:
        desenhar_linha(ras, p0, p1, PX_MM)
    ok, buf = cv2.imencode(".jpg", np.clip(ras * 255, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 85])
    ras = cv2.imdecode(buf, 0).astype(np.float32) / 255
    achados = riscos.detectar(ras, amb, np.ones(amb.shape, bool), PX_MM).riscos
    assert len(achados) == len(LINHAS)
