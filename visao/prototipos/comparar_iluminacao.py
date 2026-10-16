"""P1: quanto do comprimento de risco aparece só em `ra`, só em `rb` e nas duas
(guia 8.3 passo 6). Também mede o ângulo de cada risco em relação ao eixo longo do
aparelho: a hipótese de R1 é que risco paralelo à luz some.

`ra` = lanterna ao longo do comprimento; `rb` = ao longo da largura. Riscos a menos de
2 mm da borda ficam fora da conta principal (o brilho da moldura engana).

    uv run python -I prototipos/comparar_iluminacao.py
"""

import numpy as np

from visao import fase0


def angulo_eixo_longo(cantos):
    d = cantos[2] - cantos[1]  # lado 1→2 é longo (ordenar_cantos)
    return float(np.degrees(np.arctan2(d[1], d[0])) % 180)


def rel(angulo, eixo):
    """Ângulo entre o risco e o eixo longo, de 0 (paralelo) a 90 (perpendicular)."""
    d = abs(angulo - eixo) % 180
    return min(d, 180 - d)


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
            if a is None or not {"ra", "rb"} <= a.riscos.keys():
                continue
            eixo = angulo_eixo_longo(a.cantos)
            for incluir_borda in (False, True):
                ra = [r for r, b in zip(a.riscos["ra"], a.perto_borda["ra"]) if incluir_borda or not b]
                rb = [r for r, b in zip(a.riscos["rb"], a.perto_borda["rb"]) if incluir_borda or not b]
                so_ra = [r for r in ra if not fase0.coincide(r, rb, a.forma, a.px_mm)]
                so_rb = [r for r in rb if not fase0.coincide(r, ra, a.forma, a.px_mm)]
                ambos = [r for r in ra if r not in so_ra]
                comp = lambda rs: round(sum(r.comprimento_mm for r in rs), 1)  # noqa: E731
                ang = lambda rs: round(float(np.mean([rel(r.angulo_graus, eixo) for r in rs])), 1) if rs else ""  # noqa: E731
                total = comp(so_ra) + comp(so_rb) + comp(ambos)
                linhas.append({
                    "aparelho": n, "face": face, "inclui_borda": incluir_borda,
                    "n_so_ra": len(so_ra), "n_so_rb": len(so_rb), "n_ambos": len(ambos),
                    "mm_so_ra": comp(so_ra), "mm_so_rb": comp(so_rb), "mm_ambos": comp(ambos),
                    "pct_mm_perdido_so_com_ra": round(100 * comp(so_rb) / total, 1) if total else "",
                    "pct_mm_perdido_so_com_rb": round(100 * comp(so_ra) / total, 1) if total else "",
                    "angulo_medio_so_ra": ang(so_ra), "angulo_medio_so_rb": ang(so_rb), "angulo_medio_ambos": ang(ambos),
                    "n_uniao": len(a.riscos.get("uniao", [])),
                })
                if not incluir_borda:
                    l = linhas[-1]
                    print(f"ap{n} {face}: só ra {l['n_so_ra']} ({l['mm_so_ra']} mm) · só rb {l['n_so_rb']} "
                          f"({l['mm_so_rb']} mm) · ambos {l['n_ambos']} ({l['mm_ambos']} mm)")
    print(fase0.escrever_csv(fase0.DIR_SAIDA / "iluminacao.csv", linhas))


if __name__ == "__main__":
    comparar()
