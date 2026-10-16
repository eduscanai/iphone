"""P3: nitidez com o foco travado no aparelho deitado (guia 8.3 passo 8, R2, R3).

Mede a largura de borda 10–90% (em px e mm) e a variância do Laplaciano em:
`frente_amb` (referência, deitado), `foco_lateral`, `foco_ponta`, `lat_amb`,
`espelho_amb` e `espelho_ra`.

A região medida é a faixa da borda do aparelho, achada pelo contorno. No espelho, a
borda que interessa é a refletida: informe a região em fotos/rois.csv
(`arquivo,x,y,w,h`, em px). Sem isso, usa a imagem toda fora do aparelho deitado.

    uv run python -I prototipos/profundidade_foco.py
"""

import csv

import cv2
import numpy as np

from visao import fase0, geometria
from visao.io_imagem import ler

FOTOS = [("frente", "amb"), ("lat", "amb"), ("foco", "lateral"), ("foco", "ponta"), ("espelho", "amb"), ("espelho", "ra")]


def ler_rois():
    caminho = fase0.DIR_FOTOS / "rois.csv"
    if not caminho.exists():
        return {}
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        return {l["arquivo"].strip(): tuple(int(l[k]) for k in "xywh") for l in csv.DictReader(f)}


def largura_borda(cinza, regiao, n_max=400, meia=30):
    """Mediana da largura 10–90% das bordas mais fortes da região, em px.

    Os pontos de borda são escolhidos num gradiente suavizado (σ = 2 px), para que uma
    borda borrada vença o ruído; o perfil é medido na imagem original e só conta se
    cobrir ao menos metade do contraste da região."""
    g = cv2.GaussianBlur(cinza, (0, 0), 2.0)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    mag = cv2.magnitude(gx, gy)
    v = mag[regiao]
    if v.size == 0:
        return None
    limiar = np.percentile(v, 99.5)
    ys, xs = np.nonzero(regiao & (mag >= limiar))
    if len(ys) < 20:
        return None
    sel = np.random.default_rng(0).choice(len(ys), min(n_max, len(ys)), replace=False)
    t = np.arange(-meia, meia + 0.01, 0.25)
    p5, p95 = np.percentile(cinza[regiao], [5, 95])
    contraste_min = 0.5 * (p95 - p5)
    larguras = []
    h, w = cinza.shape
    for y, x in zip(ys[sel], xs[sel]):
        nx, ny = gx[y, x] / mag[y, x], gy[y, x] / mag[y, x]
        px, py = x + t * nx, y + t * ny
        if px.min() < 0 or py.min() < 0 or px.max() >= w - 1 or py.max() >= h - 1:
            continue
        perfil = cv2.remap(cinza, px.astype(np.float32)[None], py.astype(np.float32)[None], cv2.INTER_LINEAR)[0]
        c = len(t) // 2  # o perfil sobe do escuro (antes de c) para o claro (depois)
        lo, hi = perfil[: c + 1].min(), perfil[c:].max()
        if hi - lo < max(contraste_min, 0.02):
            continue
        p = (perfil - lo) / (hi - lo)
        abaixo = np.nonzero(p[: c + 1] <= 0.1)[0]  # mais perto do centro: ignora frisos ao lado
        acima = np.nonzero(p[c:] >= 0.9)[0]
        if len(abaixo) and len(acima):
            larguras.append((c + acima[0] - abaixo[-1]) * 0.25)
    return float(np.median(larguras)) if len(larguras) >= 10 else None


def faixa_do_espelho(forma, ap, dims_f, px_mm, marcadores, ate_mm=40.0):
    """Sem ROI: faixa de 2 a 40 mm ao redor do aparelho deitado (onde ficam os espelhos),
    sem a folha de marcadores (bordas nítidas que enganam). Distâncias por transformada
    de distância: dilatar com núcleo de 40 mm na imagem inteira é lento demais."""
    m = geometria.mascara_face(forma, ap.cantos, dims_f, 0.0, px_mm=px_mm)
    dist_aparelho = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5) / px_mm
    regiao = (dist_aparelho > 2.0) & (dist_aparelho < ate_mm)
    if marcadores:
        folha = np.ones(forma, np.uint8)
        for mk in marcadores:
            cv2.fillConvexPoly(folha, np.round(mk.cantos).astype(np.int32), 0)
        regiao &= cv2.distanceTransform(folha, cv2.DIST_L2, 5) / px_mm > 15.0
    return regiao


def laplaciano(cinza, regiao):
    lap = cv2.Laplacian(cinza * 255, cv2.CV_32F, ksize=3)
    return float(lap[regiao].var())


def medir():
    cat = fase0.catalogo()
    anot = fase0.ler_anotacao()
    rois = ler_rois()
    linhas = []
    for n in fase0.aparelhos(cat):
        try:
            dims = fase0.dimensoes_modelo(anot.modelo(n))
        except ValueError:
            continue
        ref = None
        for face, luz in FOTOS:
            foto = cat.get((n, face, luz))
            if foto is None:
                continue
            cinza = ler(foto.caminho).cinza
            dims_f = fase0.dims_da_foto(face, luz, dims)
            marcadores = geometria.detectar_aruco(cinza)
            px_aruco = geometria.px_por_mm_aruco(marcadores)
            ap = geometria.encontrar_aparelho(cinza, dims_f, fase0.escala_para_busca(px_aruco, face, luz, dims))
            px_mm = ap.px_por_mm if ap else px_aruco
            if foto.caminho.name in rois:
                x, y, w, h = rois[foto.caminho.name]
                regiao = np.zeros(cinza.shape, bool)
                regiao[y : y + h, x : x + w] = True
                tipo = "roi"
            elif ap is not None and face != "espelho":
                m = geometria.mascara_face(cinza.shape, ap.cantos, dims_f, 0.0, px_mm=px_mm)
                fora = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
                dentro = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
                regiao = np.maximum(fora, dentro) <= px_mm  # faixa de ±1 mm na borda
                tipo = "borda_do_aparelho"
            elif ap is not None:
                regiao = faixa_do_espelho(cinza.shape, ap, dims_f, px_mm, marcadores)
                tipo = "auto_ao_lado_do_aparelho"
            else:
                print(f"ap{n} {face}_{luz}: contorno não encontrado e sem ROI; pulando")
                continue
            lb = largura_borda(cinza, regiao)
            linha = {
                "aparelho": n, "foto": f"{face}_{luz}", "arquivo": foto.caminho.name, "regiao": tipo,
                "px_mm": round(px_mm, 2) if px_mm else "",
                "largura_borda_px": round(lb, 2) if lb else "",
                "largura_borda_mm": round(lb / px_mm, 3) if lb and px_mm else "",
                "laplaciano_var": round(laplaciano(cinza, regiao), 1),
            }
            if (face, luz) == ("frente", "amb"):
                ref = lb
            linha["largura_vs_deitado"] = round(lb / ref, 2) if lb and ref else ""
            linhas.append(linha)
            ys, xs = np.nonzero(regiao)
            i = len(ys) // 2
            base = fase0.base_conferencia(cinza)
            fase0.salvar(fase0.recorte_1x1(base, (xs[i], ys[i]), 500), fase0.DIR_SAIDA / "foco" / f"ap{n}_{face}_{luz}.jpg", None)
            print(f"ap{n} {face}_{luz} ({tipo}): borda {linha['largura_borda_px']} px · {linha['largura_vs_deitado']}× deitado")
    print(fase0.escrever_csv(fase0.DIR_SAIDA / "foco.csv", linhas))


if __name__ == "__main__":
    medir()
