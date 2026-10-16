"""Confere as fotos da fase 0 contra o protocolo (guia 8.2): nomes, fotos faltando,
modelo e dimensões de cada aparelho na anotação.

    uv run python -I prototipos/conferir_fotos.py
"""

from collections import defaultdict

from visao import fase0

OBRIGATORIAS = [("frente", "amb"), ("frente", "ra"), ("frente", "rb"), ("traseira", "amb"),
                ("traseira", "ra"), ("traseira", "rb"), ("lat", "amb"), ("lat", "ra")]
OPCIONAIS = [("frente", "sil"), ("foco", "lateral"), ("foco", "ponta"), ("espelho", "amb"),
             ("espelho", "ra"), ("espelho_frente", "ra"), ("sujo", "ra")]


def conferir() -> list[str]:
    cat = fase0.catalogo()
    anot = fase0.ler_anotacao()
    problemas = []
    if not cat:
        return [f"nenhuma foto em {fase0.DIR_FOTOS}"]
    por_aparelho = defaultdict(set)
    for n, face, luz in cat:
        por_aparelho[n].add((face, luz))
    for n in sorted(por_aparelho):
        tem = por_aparelho[n]
        falta = [f"{f}_{l}" for f, l in OBRIGATORIAS if (f, l) not in tem]
        opc = [f"{f}_{l}" for f, l in OPCIONAIS if (f, l) not in tem]
        desconhecidas = sorted(f"{f}_{l}" for f, l in tem if (f, l) not in OBRIGATORIAS + OPCIONAIS)
        modelo = anot.modelo(n)
        try:
            dims = fase0.dimensoes_modelo(modelo)
            txt_modelo = f"{modelo} {dims}"
        except ValueError as e:
            txt_modelo = f"PROBLEMA: {e}"
            problemas.append(f"ap{n}: {e}")
        print(f"ap{n}: {len(tem)} fotos · modelo {txt_modelo}")
        if falta:
            print(f"   faltam (obrigatórias): {', '.join(falta)}")
            problemas.append(f"ap{n}: faltam {', '.join(falta)}")
        if opc:
            print(f"   ausentes (opcionais): {', '.join(opc)}")
        if desconhecidas:
            print(f"   nomes não previstos: {', '.join(desconhecidas)}")
    if not anot.linhas:
        problemas.append("anotacao.csv ausente ou vazio")
    return problemas


if __name__ == "__main__":
    problemas = conferir()
    print("\nOK: tudo certo para rodar a análise." if not problemas else "\nPendências:\n- " + "\n- ".join(problemas))
