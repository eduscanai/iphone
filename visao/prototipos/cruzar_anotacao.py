"""P5: "o técnico viu × o algoritmo achou" e poeira (guia 8.3 passo 9).

1. Por aparelho e face: riscos anotados pelo técnico × riscos da camada (a) (união de
   ra e rb, longe da borda). Defeitos de outros tipos (amassado, trinca…) são listados
   à parte: a camada (a) só procura riscos.
2. Poeira: `sujo_ra` × `frente_ra` do mesmo aparelho, as duas sem subtrair a ambiente
   (a foto suja não tem par alinhado), com o contorno achado na própria rasante.

    uv run python -I prototipos/cruzar_anotacao.py
"""

import numpy as np

from visao import fase0, geometria
from visao import riscos as camada_a
from visao.io_imagem import ler

CURTO_MM = 3.0


def _num(texto):
    try:
        return float(str(texto).replace(",", "."))
    except ValueError:
        return None


def _sim(texto):
    return str(texto).strip().lower() in ("sim", "s", "1", "true", "x", "yes")


def cruzar():
    cat = fase0.catalogo()
    anot = fase0.ler_anotacao()
    linhas = []
    for n in fase0.aparelhos(cat):
        try:
            dims = fase0.dimensoes_modelo(anot.modelo(n))
        except ValueError:
            continue
        notas = {l.get("nota_tecnico") for l in anot.do_aparelho(n) if l.get("nota_tecnico")}
        for face in ("frente", "traseira"):
            a = fase0.analisar_face(cat, n, face, dims)
            tec = [l for l in anot.do_aparelho(n) if l.get("face", "").lower().startswith(face[:4])]
            tec_riscos = [l for l in tec if "risc" in l.get("tipo", "").lower()]
            outros = sorted({l.get("tipo", "") for l in tec if l not in tec_riscos and l.get("tipo")})
            tamanhos = [t for t in (_num(l.get("tamanho_mm_aprox", "")) for l in tec_riscos) if t]
            linha = {
                "aparelho": n, "modelo": anot.modelo(n), "face": face, "nota_tecnico": "/".join(sorted(notas)),
                "tec_n_riscos": len(tec_riscos),
                "tec_n_visiveis": sum(_sim(l.get("visivel_olho_nu", "")) for l in tec_riscos),
                "tec_maior_mm": max(tamanhos) if tamanhos else "",
                "tec_outros_defeitos": "; ".join(outros),
            }
            if a is not None:
                luz = "uniao" if "uniao" in a.riscos else next(iter(a.riscos))
                rs = [(r, c) for r, c, b in zip(a.riscos[luz], a.contraste_ambiente[luz], a.perto_borda[luz]) if not b]
                linha.update({
                    "alg_luz": luz,
                    "alg_n_riscos": len(rs),
                    "alg_n_ge_3mm": sum(r.comprimento_mm >= CURTO_MM for r, _ in rs),
                    "alg_maior_mm": max((r.comprimento_mm for r, _ in rs), default=""),
                    "alg_contraste_amb_mediano": round(float(np.median([c for _, c in rs])), 2) if rs else "",
                    "alg_n_perto_borda": sum(a.perto_borda[luz]),
                    "concorda_tem_risco": (len(tec_riscos) > 0) == (len(rs) > 0),
                })
            linhas.append(linha)
            print(f"ap{n} {face}: técnico {linha['tec_n_riscos']} riscos · algoritmo {linha.get('alg_n_riscos', '—')} "
                  f"({linha.get('alg_n_ge_3mm', '—')} ≥ 3 mm)")
    print(fase0.escrever_csv(fase0.DIR_SAIDA / "cruzamento.csv", linhas))
    poeira(cat, anot)


def _riscos_sem_ambiente(caminho, dims_f):
    img = ler(caminho).cinza
    px_aruco = geometria.px_por_mm_aruco(geometria.detectar_aruco(img))
    ap = geometria.encontrar_aparelho(img, dims_f, px_aruco)  # frente deitada: escala da mesa serve
    if ap is None:
        return None, None, None
    m = geometria.mascara_face(img.shape, ap.cantos, dims_f, fase0.config.PARAM_RISCOS.borda_excluida_mm, px_mm=ap.px_por_mm)
    m_borda = geometria.mascara_face(img.shape, ap.cantos, dims_f, fase0.config.PARAM_RISCOS.perto_borda_mm, px_mm=ap.px_por_mm)
    rs = camada_a.detectar(img, None, m, ap.px_por_mm).riscos
    rs = [r for r in rs if m_borda[r.esqueleto_px[:, 1], r.esqueleto_px[:, 0]].all()]
    return rs, img, ap


def poeira(cat, anot):
    linhas = []
    for n in fase0.aparelhos(cat):
        if (n, "sujo", "ra") not in cat or (n, "frente", "ra") not in cat:
            continue
        try:
            dims_f = fase0.dims_da_foto("frente", "ra", fase0.dimensoes_modelo(anot.modelo(n)))
        except ValueError:
            continue
        for estado, chave in (("sujo", (n, "sujo", "ra")), ("limpo", (n, "frente", "ra"))):
            rs, img, ap = _riscos_sem_ambiente(cat[chave].caminho, dims_f)
            if rs is None:
                print(f"ap{n} {estado}: contorno não encontrado")
                continue
            curtos = [r for r in rs if r.comprimento_mm < CURTO_MM]
            linhas.append({
                "aparelho": n, "estado": estado, "n_riscos": len(rs), "n_curtos_lt_3mm": len(curtos),
                "mm_total": round(sum(r.comprimento_mm for r in rs), 1),
                "mm_curtos": round(sum(r.comprimento_mm for r in curtos), 1),
            })
            base = fase0.base_conferencia(img)
            fase0.desenhar_cantos(base, ap.cantos)
            fase0.desenhar_riscos(base, rs, fase0.CORES["ra"])
            fase0.salvar(base, fase0.DIR_SAIDA / "poeira" / f"ap{n}_{estado}.jpg")
            print(f"ap{n} {estado}: {len(rs)} riscos ({len(curtos)} < 3 mm)")
    print(fase0.escrever_csv(fase0.DIR_SAIDA / "poeira.csv", linhas))


if __name__ == "__main__":
    cruzar()
