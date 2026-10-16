"""P2 e P4: escala (px/mm) pelos ArUco e pelo contorno do aparelho, com e sem a foto
de contraluz (guia 8.3 passos 4 e 10).

Os ArUco ficam na mesa; a face do aparelho fica `z` mm acima. Com a câmera a `H` mm
da mesa, a face aparece maior por H ÷ (H − z). Com as duas escalas, estima-se H.

    uv run python -I prototipos/medir_escala.py [--altura-mm 250]
"""

import argparse


from visao import config, fase0, geometria
from visao.io_imagem import ler

# Foto → (face nas dimensões, altura da face acima da mesa)
FOTOS = [("frente", "amb"), ("traseira", "amb"), ("lat", "amb"), ("foco", "lateral"), ("foco", "ponta"), ("espelho", "amb")]


def medir(altura_mm: float):
    cat = fase0.catalogo()
    anot = fase0.ler_anotacao()
    linhas = []
    for n in fase0.aparelhos(cat):
        try:
            dims = fase0.dimensoes_modelo(anot.modelo(n))
        except ValueError as e:
            print(f"ap{n}: {e}")
            continue
        for face, luz in FOTOS:
            foto = cat.get((n, face, luz))
            if foto is None:
                continue
            img = ler(foto.caminho)
            dims_f = fase0.dims_da_foto(face, luz, dims)
            z = fase0.altura_da_face_mm(face, luz, dims)
            marcadores = geometria.detectar_aruco(img.cinza)
            px_aruco = geometria.px_por_mm_aruco(marcadores)
            sil = cat.get((n, face, "sil")) if luz == "amb" else None
            variantes = [("sem_contraluz", None)]
            if sil:
                variantes.append(("com_contraluz", ler(sil.caminho).cinza))
            for variante, img_sil in variantes:
                ap = geometria.encontrar_aparelho(
                    img.cinza, dims_f, fase0.escala_para_busca(px_aruco, face, luz, dims), silhueta=img_sil
                )
                linha = {
                    "aparelho": n,
                    "modelo": anot.modelo(n),
                    "foto": f"{face}_{luz}",
                    "arquivo": foto.caminho.name,
                    "formato": foto.formato,
                    "largura_px": img.largura,
                    "altura_px": img.altura,
                    "variante": variante,
                    "n_aruco": len(marcadores),
                    "px_mm_aruco": round(px_aruco, 3) if px_aruco else "",
                    "contorno_ok": ap is not None and not ap.fora_do_quadro,
                }
                if ap is not None:
                    esperado = px_aruco * altura_mm / (altura_mm - z) if px_aruco else None
                    linha.update(
                        fonte_contorno=ap.fonte,
                        fora_do_quadro=ap.fora_do_quadro,
                        px_mm_aparelho=round(ap.px_por_mm, 3),
                        px_mm_curto=round(ap.px_por_mm_curto, 3),
                        px_mm_longo=round(ap.px_por_mm_longo, 3),
                        residuo_bordas_mm=round(ap.residuo_bordas_mm, 3),
                        residuo_p99_mm=round(ap.residuo_max_mm, 3),
                        dif_aruco_pct=round((ap.px_por_mm / px_aruco - 1) * 100, 2) if px_aruco else "",
                        dif_corrigida_pct=round((ap.px_por_mm / esperado - 1) * 100, 2) if esperado else "",
                        altura_estimada_mm=(
                            round(z * ap.px_por_mm / (ap.px_por_mm - px_aruco), 0)
                            if px_aruco and ap.px_por_mm > px_aruco * 1.002 else ""
                        ),
                        campo_util_mm=round(img.largura / ap.px_por_mm, 1),
                        altura_para_20pxmm=round(altura_mm * ap.px_por_mm / 20, 0) if luz == "amb" and face in ("frente", "traseira") else "",
                    )
                    base = fase0.base_conferencia(img.cinza)
                    fase0.desenhar_cantos(base, ap.cantos)
                    for m in marcadores:
                        fase0.desenhar_cantos(base, m.cantos, fase0.CORES["aruco"])
                    fase0.salvar(base, fase0.DIR_SAIDA / "escala" / f"ap{n}_{face}_{luz}_{variante}.jpg")
                linhas.append(linha)
                print(
                    f"ap{n} {face}_{luz} {variante}: aruco {linha['px_mm_aruco'] or '—'} px/mm · "
                    f"aparelho {linha.get('px_mm_aparelho', 'FALHOU')} · dif corrigida {linha.get('dif_corrigida_pct', '—')}%"
                )
    caminho = fase0.escrever_csv(fase0.DIR_SAIDA / "escala.csv", linhas)
    print(caminho)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--altura-mm", type=float, default=config.ALTURA_CAMERA_MM_PADRAO,
                    help="distância da lente até a mesa usada nas fotos")
    medir(ap.parse_args().altura_mm)
