"""P1 e P5: camada (a) em `ra`, `rb` e na união das duas (guia 8.3 passo 5).

Saídas: saida/riscos.csv (um risco por linha) e, por face, uma imagem com os riscos
(vermelho = só ra, azul = só rb, amarelo = nos dois) e um mosaico 1:1 dos maiores.

    uv run python -I prototipos/riscos.py [--sem-cache]
"""

import argparse

import cv2
import numpy as np

from visao import fase0, geometria
from visao.io_imagem import ler

FACES = ["frente", "traseira"]


def rodar(usar_cache=True):
    cat = fase0.catalogo()
    anot = fase0.ler_anotacao()
    linhas, faces = [], []
    for n in fase0.aparelhos(cat):
        try:
            dims = fase0.dimensoes_modelo(anot.modelo(n))
        except ValueError as e:
            print(f"ap{n}: {e}")
            continue
        for face in FACES:
            a = fase0.analisar_face(cat, n, face, dims, usar_cache)
            if a is None:
                continue
            for luz, lista in a.riscos.items():
                outra = {"ra": "rb", "rb": "ra"}.get(luz)
                for i, r in enumerate(lista):
                    centro_mm = geometria.px_para_mm(r.caminho_px.mean(axis=0, keepdims=True), a.cantos, a.dims_mm)[0]
                    linhas.append({
                        "aparelho": n, "modelo": anot.modelo(n), "face": face, "luz": luz, "id": i,
                        "comprimento_mm": r.comprimento_mm, "largura_mm": r.largura_mm,
                        "angulo_graus": r.angulo_graus, "contraste": r.contraste,
                        "contraste_ambiente": a.contraste_ambiente[luz][i],
                        "perto_borda": a.perto_borda[luz][i],
                        "tambem_na_outra_luz": (
                            fase0.coincide(r, a.riscos.get(outra, []), a.forma, a.px_mm) if outra in a.riscos else ""
                        ),
                        "x_mm": round(float(centro_mm[0]), 1), "y_mm": round(float(centro_mm[1]), 1),
                        "px_mm": round(a.px_mm, 2),
                    })
            imagens(cat, a)
            faces.append({
                "aparelho": n, "face": face, "px_mm": round(a.px_mm, 2), "fonte_contorno": a.fonte_contorno,
                "residuo_bordas_mm": round(a.residuo_bordas_mm, 3),
                "deslocamento_max_px": round(max((max(abs(dx), abs(dy)) for dx, dy in a.deslocamentos.values()), default=0), 2),
                **{f"n_{l}": len(v) for l, v in a.riscos.items()},
                **{f"n_{l}_perto_borda": sum(a.perto_borda[l]) for l in a.riscos},
            })
            resumo = " · ".join(f"{l}: {len(v)}" for l, v in a.riscos.items())
            print(f"ap{n} {face}: {a.px_mm:.1f} px/mm · contorno {a.fonte_contorno} · desloc {a.deslocamentos} · {resumo}")
    print(fase0.escrever_csv(fase0.DIR_SAIDA / "riscos.csv", linhas))
    print(fase0.escrever_csv(fase0.DIR_SAIDA / "faces.csv", faces))


def imagens(cat, a: fase0.AnaliseFace):
    n, face = a.aparelho, a.face
    fotos = [cat[(n, face, l)] for l in ("ra", "rb") if (n, face, l) in cat]
    mascara = geometria.mascara_face(a.forma, a.cantos, a.dims_mm, 0.0, px_mm=a.px_mm)
    fundo = np.maximum.reduce([ler(f.caminho).cinza for f in fotos])
    base = fase0.base_conferencia(fundo, mascara)
    limpa = base.copy()
    fase0.desenhar_cantos(base, a.cantos)
    ra, rb = a.riscos.get("ra", []), a.riscos.get("rb", [])
    so_ra = [r for r in ra if not fase0.coincide(r, rb, a.forma, a.px_mm)]
    so_rb = [r for r in rb if not fase0.coincide(r, ra, a.forma, a.px_mm)]
    ambos = [r for r in ra if r not in so_ra]
    fase0.desenhar_riscos(base, so_ra, fase0.CORES["ra"])
    fase0.desenhar_riscos(base, so_rb, fase0.CORES["rb"])
    fase0.desenhar_riscos(base, ambos, fase0.CORES["ambos"])
    fase0.salvar(base, fase0.DIR_SAIDA / "riscos" / f"ap{n}_{face}.jpg")

    maiores = sorted(a.riscos.get("uniao", ra + rb), key=lambda r: -r.comprimento_mm)[:6]
    if maiores:
        anotada = limpa.copy()
        fase0.desenhar_riscos(anotada, a.riscos.get("uniao", ra + rb), fase0.CORES["ambos"], espessura=1, rotulo=False)
        blocos = []
        for r in maiores:
            c = r.caminho_px.mean(axis=0)
            par = np.hstack([fase0.recorte_1x1(limpa, c), fase0.recorte_1x1(anotada, c)])
            cv2.putText(par, f"{r.comprimento_mm:.1f} mm", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            blocos.append(par)
        fase0.salvar(np.vstack(blocos), fase0.DIR_SAIDA / "riscos" / f"ap{n}_{face}_zoom.jpg", lado_max=None)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sem-cache", action="store_true")
    rodar(not ap.parse_args().sem_cache)
