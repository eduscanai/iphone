"""Folha de marcadores ArUco em escala 1:1 (guia 8.3 passo 2).

4 marcadores DICT_4X4_50 (ids 0 a 3) de 30 mm, margem branca de 5 mm marcada com
linha de corte, régua de 100 mm para conferir a escala da impressão. PDF A4.

    uv run python -I prototipos/gerar_marcadores.py [--saida caminho.pdf]
"""

import argparse
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from visao import config  # noqa: E402
from visao.fase0 import DIR_SAIDA  # noqa: E402

A4 = (210.0, 297.0)
MARGEM_MM = 5.0


def desenhar_marcador(ax, dic, ident, x, y, lado_mm):
    """Marcador como retângulos vetoriais: imagens raster no PDF são encaixadas na
    grade de 72 dpi do matplotlib e erram o tamanho em até ~0,25 mm."""
    celulas = 4 + 2  # 4×4 bits + borda preta de 1 célula
    bits = cv2.aruco.generateImageMarker(dic, ident, celulas)
    c = lado_mm / celulas
    for lin in range(celulas):
        col = 0
        while col < celulas:  # junta células pretas vizinhas da mesma linha
            if bits[lin, col] == 0:
                ini = col
                while col < celulas and bits[lin, col] == 0:
                    col += 1
                ax.add_patch(Rectangle((x + ini * c, y + lin * c), (col - ini) * c, c, lw=0, fc="k", antialiased=False))
            else:
                col += 1


def gerar(saida: Path, lado_mm: float = config.LADO_ARUCO_MM):
    dic = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, config.DICIONARIO_ARUCO))
    fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4[0])
    ax.set_ylim(A4[1], 0)  # y para baixo, em mm
    ax.axis("off")

    ax.text(15, 18, "Morecheck · marcadores ArUco da cabine", fontsize=13, weight="bold")
    ax.text(15, 25, "Imprima em 100% (tamanho real, sem “ajustar à página”).", fontsize=9)
    ax.text(15, 30, f"Confira com a régua: cada quadrado preto mede {lado_mm:.1f} mm e a régua mede 100 mm.".replace(".0 mm", ",0 mm"), fontsize=9)
    ax.text(15, 35, f"{config.DICIONARIO_ARUCO}, ids 0 a 3. Corte na linha tracejada (margem branca de {MARGEM_MM:.0f} mm).", fontsize=9)

    passo = lado_mm + 2 * MARGEM_MM + 20
    origem_x, origem_y = 35.0, 50.0
    for i in range(4):
        x = origem_x + (i % 2) * passo + MARGEM_MM
        y = origem_y + (i // 2) * passo + MARGEM_MM
        desenhar_marcador(ax, dic, i, x, y, lado_mm)
        ax.add_patch(
            Rectangle((x - MARGEM_MM, y - MARGEM_MM), lado_mm + 2 * MARGEM_MM, lado_mm + 2 * MARGEM_MM,
                      fill=False, lw=0.4, ls=(0, (4, 3)), ec="0.5")
        )
        ax.text(x + lado_mm / 2, y + lado_mm + MARGEM_MM + 4, f"id {i}", ha="center", fontsize=8, color="0.3")

    # régua de 100 mm
    rx, ry = 55.0, 215.0
    ax.plot([rx, rx + 100], [ry, ry], color="k", lw=0.6)
    for mm in range(101):
        alt = 6 if mm % 10 == 0 else (4 if mm % 5 == 0 else 2.5)
        ax.plot([rx + mm, rx + mm], [ry, ry - alt], color="k", lw=0.35)
        if mm % 10 == 0:
            ax.text(rx + mm, ry - 7.5, str(mm), ha="center", fontsize=6)
    ax.text(rx + 50, ry + 6, "régua de conferência: 100 mm", ha="center", fontsize=8)

    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida, format="pdf")
    plt.close(fig)
    return saida


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, default=DIR_SAIDA / "marcadores.pdf")
    args = ap.parse_args()
    print(gerar(args.saida))
