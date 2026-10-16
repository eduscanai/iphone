"""Imagens sintéticas para os testes (guia 17.1)."""

import cv2
import numpy as np


def fundo(alt_mm, larg_mm, px_mm, nivel=0.05, ruido=0.008, semente=0):
    rng = np.random.default_rng(semente)
    h, w = round(alt_mm * px_mm), round(larg_mm * px_mm)
    return (nivel + rng.normal(0, ruido, (h, w))).astype(np.float32)


def desenhar_linha(img, p0_mm, p1_mm, px_mm, intensidade=0.12, sub=8):
    """Linha antisserrilhada de ~1 px de largura, com extremos exatos (em mm)."""
    h, w = img.shape
    camada = np.zeros((h, w), np.float32)
    p0 = tuple(round(v * px_mm * sub) for v in p0_mm)
    p1 = tuple(round(v * px_mm * sub) for v in p1_mm)
    cv2.line(camada, p0, p1, intensidade, 1, cv2.LINE_AA, shift=3)
    img += cv2.GaussianBlur(camada, (0, 0), 0.6)
    return img


def desenhar_poeira(img, n, px_mm, semente=1, intensidade=0.3, margem_mm=5):
    rng = np.random.default_rng(semente)
    h, w = img.shape
    m = int(margem_mm * px_mm)
    centros = []
    for _ in range(n):
        x, y = int(rng.integers(m, w - m)), int(rng.integers(m, h - m))
        r = int(rng.integers(1, 4))
        cv2.circle(img, (x, y), r, float(img[y, x] + intensidade), -1, cv2.LINE_AA)
        centros.append((x, y))
    return centros


def retangulo_arredondado(larg_mm, alt_mm, raio_mm, px_mm, sub=4):
    """Máscara float (0..1) do aparelho no referencial em mm, superamostrada."""
    s = px_mm * sub
    m = np.zeros((round(alt_mm * s), round(larg_mm * s)), np.uint8)
    r = round(raio_mm * s)
    w, h = m.shape[1], m.shape[0]
    cv2.rectangle(m, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(m, (0, r), (w, h - r), 255, -1)
    for c in [(r, r), (w - r, r), (w - r, h - r), (r, h - r)]:
        cv2.circle(m, c, r, 255, -1)
    return cv2.resize(m, (round(larg_mm * px_mm), round(alt_mm * px_mm)), interpolation=cv2.INTER_AREA) / 255.0
