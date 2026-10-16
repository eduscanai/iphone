"""P2: riscos perdidos quando a imagem é reduzida para 10, 15 e 20 px/mm
(guia 8.3 passo 7, R4). Referência: a detecção na resolução nativa.

    uv run python -I prototipos/comparar_resolucao.py
"""

import copy

import cv2
import numpy as np

from visao import fase0, geometria
from visao import riscos as camada_a
from visao.io_imagem import ler

ALVOS = [10, 15, 20]
FAIXAS = [(0, 3, "< 3 mm"), (3, 5, "3–5 mm"), (5, 15, "5–15 mm"), (15, 1e9, "> 15 mm")]


def faixa(comp):
    return next(nome for lo, hi, nome in FAIXAS if lo <= comp < hi)


def reduzir(img, f):
    return cv2.resize(img, (round(img.shape[1] * f), round(img.shape[0] * f)), interpolation=cv2.INTER_AREA)


def ampliar_risco(r, f):
    """Leva um risco detectado na imagem reduzida para as coordenadas nativas."""
    r2 = copy.copy(r)
    r2.caminho_px = r.caminho_px / f
    pts = r.esqueleto_px / f
    # repovoa o esqueleto ampliado ao longo do caminho (senão fica pontilhado)
    densos = []
    for p0, p1 in zip(r2.caminho_px[:-1], r2.caminho_px[1:]):
        k = max(int(np.ceil(np.linalg.norm(p1 - p0))), 1)
        densos.append(p0 + (p1 - p0) * np.linspace(0, 1, k, endpoint=False)[:, None])
    densos.append(r2.caminho_px[-1:])
    r2.esqueleto_px = np.round(np.vstack([pts] + densos)).astype(int)
    x, y, w, h = r.caixa_px
    r2.caixa_px = (int(x / f), int(y / f), int(np.ceil(w / f)) + 1, int(np.ceil(h / f)) + 1)
    return r2


def comparar():
    cat = fase0.catalogo()
    anot = fase0.ler_anotacao()
    linhas = []
    for n in fase0.aparelhos(cat):
        try:
            dims = fase0.dimensoes_modelo(anot.modelo(n))
        except ValueError:
            continue
        for face in ("frente", "traseira"):
            a = fase0.analisar_face(cat, n, face, dims)
            if a is None:
                continue
            mascara = geometria.mascara_face(a.forma, a.cantos, a.dims_mm, a.mascara_borda_mm, px_mm=a.px_mm)
            amb = ler(cat[(n, face, "amb")].caminho).cinza
            for luz in ("ra", "rb"):
                if luz not in a.riscos:
                    continue
                ras, _ = geometria.alinhar(amb, ler(cat[(n, face, luz)].caminho).cinza, mascara)
                nativos = [r for r, b in zip(a.riscos[luz], a.perto_borda[luz]) if not b]
                perdidos_10 = []
                for alvo in ALVOS:
                    f = alvo / a.px_mm
                    if f > 0.95:
                        print(f"ap{n} {face} {luz}: nativo ({a.px_mm:.1f} px/mm) já é ≤ {alvo} px/mm; pulando")
                        continue
                    m_red = reduzir(mascara.astype(np.uint8), f).astype(bool)
                    achados = camada_a.detectar(reduzir(ras, f), reduzir(amb, f), m_red, alvo).riscos
                    ampliados = [ampliar_risco(r, f) for r in achados]
                    for lo, hi, nome in FAIXAS:
                        grupo = [r for r in nativos if lo <= r.comprimento_mm < hi]
                        achou = [r for r in grupo if fase0.coincide(r, ampliados, a.forma, a.px_mm)]
                        if alvo == 10:
                            perdidos_10 += [r for r in grupo if r not in achou]
                        linhas.append({
                            "aparelho": n, "face": face, "luz": luz, "px_mm_nativo": round(a.px_mm, 1),
                            "px_mm_alvo": alvo, "faixa": nome, "n_nativo": len(grupo), "n_achados": len(achou),
                            "pct_achados": round(100 * len(achou) / len(grupo), 1) if grupo else "",
                            "mm_nativo": round(sum(r.comprimento_mm for r in grupo), 1),
                            "mm_achados": round(sum(r.comprimento_mm for r in achou), 1),
                        })
                    print(f"ap{n} {face} {luz} @ {alvo} px/mm: {len(achados)} riscos (nativo: {len(nativos)})")
                if perdidos_10:
                    base = fase0.base_conferencia(ras, mascara)
                    fase0.desenhar_cantos(base, a.cantos)
                    fase0.desenhar_riscos(base, perdidos_10, fase0.CORES["perdido"])
                    fase0.salvar(base, fase0.DIR_SAIDA / "resolucao" / f"ap{n}_{face}_{luz}_perdidos_10pxmm.jpg")
    print(fase0.escrever_csv(fase0.DIR_SAIDA / "resolucao.csv", linhas))


if __name__ == "__main__":
    comparar()
