"""Contorno do aparelho, retas das bordas, cantos e escala (guia 15.3).

Estratégia:
1. Achar candidatos a contorno numa versão reduzida da imagem (vários limiares).
2. Escolher o candidato cuja proporção (e área, se a escala ArUco for conhecida)
   bate com as dimensões da face.
3. Refinar cada borda na resolução nativa: perfis perpendiculares à borda, posição
   subpixel do maior gradiente, reta ajustada com perda de Huber. Os pontos perto
   dos cantos arredondados ficam de fora.
4. Cantos virtuais = interseção das 4 retas.
"""

from dataclasses import dataclass, field

import cv2
import numpy as np
from scipy import ndimage

from . import config
from .io_imagem import para_u8

LADO_MAX_REDUZIDA = 2000


@dataclass
class Marcador:
    id: int
    cantos: np.ndarray  # 4 × 2, px
    lado_px: float


@dataclass
class Aparelho:
    cantos: np.ndarray  # 4 × 2, px; ordem horária, lado 0→1 = lado curto
    px_por_mm: float
    px_por_mm_curto: float
    px_por_mm_longo: float
    residuo_bordas_mm: float  # mediana dos resíduos das 4 bordas
    residuo_max_mm: float
    proporcao_erro: float
    fonte: str  # qual limiar achou o contorno
    fora_do_quadro: bool  # algum canto fora da imagem: reprovar ("aparelho fora do quadro")
    pontos_bordas: list[np.ndarray] = field(default_factory=list)

    @property
    def lados_px(self) -> np.ndarray:
        return np.linalg.norm(np.roll(self.cantos, -1, axis=0) - self.cantos, axis=1)


# ---------------------------------------------------------------- ArUco


def detectar_aruco(cinza: np.ndarray, lado_mm: float = config.LADO_ARUCO_MM) -> list[Marcador]:
    dicionario = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, config.DICIONARIO_ARUCO))
    parametros = cv2.aruco.DetectorParameters()
    parametros.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    detector = cv2.aruco.ArucoDetector(dicionario, parametros)
    cantos, ids, _ = detector.detectMarkers(para_u8(cinza))
    if ids is None:
        return []
    marcadores = []
    for c, i in zip(cantos, ids.ravel()):
        c = c.reshape(4, 2).astype(np.float64)
        lado = float(np.mean(np.linalg.norm(np.roll(c, -1, axis=0) - c, axis=1)))
        marcadores.append(Marcador(id=int(i), cantos=c, lado_px=lado))
    return marcadores


def px_por_mm_aruco(marcadores: list[Marcador], lado_mm: float = config.LADO_ARUCO_MM) -> float | None:
    if not marcadores:
        return None
    return float(np.mean([m.lado_px for m in marcadores])) / lado_mm


# ---------------------------------------------------------------- cantos


def ordenar_cantos(cantos: np.ndarray) -> np.ndarray:
    """Ordem horária (na imagem, y para baixo), lado 0→1 curto, canto 0 o mais
    perto do canto superior esquerdo da imagem entre as duas opções."""
    c = np.asarray(cantos, dtype=np.float64).reshape(4, 2)
    centro = c.mean(axis=0)
    ang = np.arctan2(c[:, 1] - centro[1], c[:, 0] - centro[0])
    c = c[np.argsort(ang)]  # crescente em ângulo = horário com y para baixo
    lados = np.linalg.norm(np.roll(c, -1, axis=0) - c, axis=1)
    inicio = 0 if lados[0] + lados[2] <= lados[1] + lados[3] else 1
    opcoes = [np.roll(c, -inicio, axis=0), np.roll(c, -(inicio + 2), axis=0)]
    return min(opcoes, key=lambda o: o[0].sum())


def _interseccao(l1, l2) -> np.ndarray:
    (vx1, vy1, x1, y1), (vx2, vy2, x2, y2) = l1, l2
    a = np.array([[vx1, -vx2], [vy1, -vy2]], dtype=np.float64)
    b = np.array([x2 - x1, y2 - y1], dtype=np.float64)
    t = np.linalg.solve(a, b)
    return np.array([x1 + t[0] * vx1, y1 + t[0] * vy1])


# ---------------------------------------------------------------- contorno


def _candidatos(reduzida_u8: np.ndarray, px_mm_red: float | None) -> list[tuple[str, np.ndarray]]:
    borrada = cv2.GaussianBlur(reduzida_u8, (5, 5), 0)
    mascaras = []
    _, otsu = cv2.threshold(borrada, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mascaras += [("otsu", otsu), ("otsu_inv", 255 - otsu)]

    mediana = float(np.median(borrada))
    bordas = cv2.Canny(borrada, max(5, 0.33 * mediana), max(15, 1.0 * mediana))
    k = max(5, int(round((px_mm_red or 0) * 2)) | 1) if px_mm_red else max(5, (min(reduzida_u8.shape) // 100) | 1)
    fechada = cv2.morphologyEx(bordas, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    preenchida = np.zeros_like(fechada)
    contornos, _ = cv2.findContours(fechada, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(preenchida, contornos, -1, 255, thickness=cv2.FILLED)
    mascaras.append(("bordas", preenchida))

    # Varredura de limiares: um objeto muito claro na cena (a folha de marcadores)
    # desloca o Otsu; algum nível intermediário separa o aparelho do fundo.
    niveis = np.unique(np.percentile(borrada, np.linspace(5, 99, 20)).round())
    for t in niveis:
        acima = (borrada > t).astype(np.uint8) * 255
        mascaras += [(f"nivel_{int(t)}", acima), (f"nivel_inv_{int(t)}", 255 - acima)]

    adapt = cv2.adaptiveThreshold(borrada, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, k * 4 + 1, 5)
    adapt = cv2.morphologyEx(adapt, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    mascaras.append(("adaptativo", adapt))
    return mascaras


def _melhor_contorno(mascaras, dims_mm, px_mm_red, area_img):
    w_mm, h_mm = sorted(dims_mm)
    prop_esp = h_mm / w_mm
    melhor = None
    for nome, m in mascaras:
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        contornos, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in contornos:
            area = cv2.contourArea(c)
            if area < 0.005 * area_img or area > 0.9 * area_img:
                continue
            (_, _), (rw, rh), _ = cv2.minAreaRect(c)
            if min(rw, rh) < 3:
                continue
            prop = max(rw, rh) / min(rw, rh)
            erro_prop = abs(prop / prop_esp - 1)
            if erro_prop > config.TOLERANCIA_PROPORCAO:
                continue
            erro_area = 0.0
            if px_mm_red:
                erro_area = abs(rw * rh / (w_mm * h_mm * px_mm_red**2) - 1)
                if erro_area > config.TOLERANCIA_AREA:
                    continue
            solidez = area / max(rw * rh, 1)
            nota = erro_prop + erro_area + (1 - solidez)
            if melhor is None or nota < melhor[0]:
                melhor = (nota, nome, c, erro_prop)
    return melhor


def _cantos_por_retas(pontos, caixa, raio_canto_mm, dims_mm):
    """Cantos virtuais por 4 retas ajustadas aos pontos do contorno de cada lado,
    longe dos cantos arredondados (guia 15.3, passo 3). Funciona com perspectiva,
    em que os lados não são paralelos e o retângulo mínimo erra nas pontas."""
    curto_mm = min(dims_mm)
    lados = np.linalg.norm(np.roll(caixa, -1, axis=0) - caixa, axis=1)
    px_mm = (lados[0] + lados[2]) / 2 / curto_mm
    margem = 1.5 * raio_canto_mm * px_mm
    tol = 0.08 * min(lados)
    retas = []
    for k in range(4):
        p0, p1 = caixa[k], caixa[(k + 1) % 4]
        comp = np.linalg.norm(p1 - p0)
        d = (p1 - p0) / comp
        rel = pontos - p0
        t = rel @ d
        dist = np.abs(rel @ np.array([-d[1], d[0]]))
        m = min(margem, 0.3 * comp)
        sel = pontos[(t > m) & (t < comp - m) & (dist < tol)]
        if len(sel) < 5:
            return caixa
        retas.append(cv2.fitLine(sel.astype(np.float32), cv2.DIST_HUBER, 0, 0.01, 0.01).ravel())
    return ordenar_cantos(np.array([_interseccao(retas[k - 1], retas[k]) for k in range(4)]))


def _refinar_borda(suave, p0, p1, normal, busca_px, margem_px, n=160):
    """Pontos subpixel da borda entre p0 e p1, buscando ao longo da normal."""
    comp = np.linalg.norm(p1 - p0)
    if comp <= 2 * margem_px + 10:
        margem_px = comp * 0.2
    direcao = (p1 - p0) / comp
    ts = np.linspace(margem_px, comp - margem_px, n)
    passos = np.arange(-busca_px, busca_px + 0.5, 0.5)
    base = p0[None, :] + ts[:, None] * direcao[None, :]
    pts = base[:, None, :] + passos[None, :, None] * normal[None, None, :]
    perfis = ndimage.map_coordinates(suave, [pts[..., 1].ravel(), pts[..., 0].ravel()], order=1, mode="nearest")
    perfis = perfis.reshape(len(ts), len(passos))
    grad = np.abs(np.gradient(perfis, axis=1))
    i = np.argmax(grad[:, 1:-1], axis=1) + 1
    linhas = np.arange(len(ts))
    g0, g1, g2 = grad[linhas, i - 1], grad[linhas, i], grad[linhas, i + 1]
    den = g0 - 2 * g1 + g2
    seguro = np.abs(den) > 1e-9
    delta = np.zeros_like(den)
    delta[seguro] = 0.5 * (g0 - g2)[seguro] / den[seguro]
    desloc = (passos[i] + np.clip(delta, -1, 1) * 0.5)
    forte = g1 > np.percentile(g1, 25) * 0.5  # descarta perfis sem borda
    return (base + desloc[:, None] * normal[None, :])[forte]


def encontrar_aparelho(
    cinza: np.ndarray,
    dims_mm: tuple[float, float],
    px_mm_aruco: float | None = None,
    silhueta: np.ndarray | None = None,
    raio_canto_mm: float = config.RAIO_CANTO_PADRAO_MM,
) -> Aparelho | None:
    """Acha a face do aparelho. `dims_mm` = (lado curto, lado longo) da face.

    Com `silhueta` (foto de contraluz alinhada), o contorno e o refinamento usam
    a silhueta, que tem bordas limpas.
    """
    fonte_img = silhueta if silhueta is not None else cinza
    h, w = fonte_img.shape
    fator = max(1.0, max(h, w) / LADO_MAX_REDUZIDA)
    reduzida = cv2.resize(para_u8(fonte_img), (round(w / fator), round(h / fator)), interpolation=cv2.INTER_AREA)
    px_mm_red = px_mm_aruco / fator if px_mm_aruco else None

    melhor = _melhor_contorno(_candidatos(reduzida, px_mm_red), dims_mm, px_mm_red, reduzida.size)
    if melhor is None:
        return None
    _, nome, contorno, erro_prop = melhor
    pts_red = contorno.reshape(-1, 2).astype(np.float64)
    chute = _cantos_por_retas(pts_red, ordenar_cantos(cv2.boxPoints(cv2.minAreaRect(contorno))), raio_canto_mm, dims_mm)
    chute = chute * fator
    tocando_borda = bool(
        np.any(pts_red.min(axis=0) <= 1) or pts_red[:, 0].max() >= reduzida.shape[1] - 2 or pts_red[:, 1].max() >= reduzida.shape[0] - 2
    )

    curto_mm, longo_mm = sorted(dims_mm)
    lados = np.linalg.norm(np.roll(chute, -1, axis=0) - chute, axis=1)
    px_mm_chute = (lados[0] + lados[2]) / 2 / curto_mm
    margem_px = 1.5 * raio_canto_mm * px_mm_chute
    busca_px = max(8.0, 3.0 * fator)

    suave = cv2.GaussianBlur(fonte_img.astype(np.float32), (0, 0), 1.2)
    centro = chute.mean(axis=0)
    retas, pontos_bordas = [], []
    for k in range(4):
        p0, p1 = chute[k], chute[(k + 1) % 4]
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        normal = np.array([-d[1], d[0]])
        if np.dot(normal, (p0 + p1) / 2 - centro) < 0:
            normal = -normal
        pts = _refinar_borda(suave, p0, p1, normal, busca_px, margem_px)
        if len(pts) < 10:
            return None
        reta = cv2.fitLine(pts.astype(np.float32), cv2.DIST_HUBER, 0, 0.01, 0.01).ravel()
        retas.append(reta)
        pontos_bordas.append(pts)

    cantos = np.array([_interseccao(retas[k - 1], retas[k]) for k in range(4)])
    cantos = ordenar_cantos(cantos)
    lados = np.linalg.norm(np.roll(cantos, -1, axis=0) - cantos, axis=1)
    px_curto = (lados[0] + lados[2]) / 2 / curto_mm
    px_longo = (lados[1] + lados[3]) / 2 / longo_mm
    px_mm = (px_curto + px_longo) / 2

    residuos = []
    for reta, pts in zip(retas, pontos_bordas):
        vx, vy, x0, y0 = reta
        dist = np.abs((pts[:, 0] - x0) * vy - (pts[:, 1] - y0) * vx)
        residuos.append(dist)
    todos = np.concatenate(residuos) / px_mm
    return Aparelho(
        cantos=cantos,
        px_por_mm=float(px_mm),
        px_por_mm_curto=float(px_curto),
        px_por_mm_longo=float(px_longo),
        residuo_bordas_mm=float(np.median(todos)),
        residuo_max_mm=float(np.percentile(todos, 99)),
        proporcao_erro=float(erro_prop),
        fonte=("silhueta_" if silhueta is not None else "") + nome,
        fora_do_quadro=tocando_borda
        or bool(np.any(cantos < 0) or np.any(cantos[:, 0] > w - 1) or np.any(cantos[:, 1] > h - 1)),
        pontos_bordas=pontos_bordas,
    )


# ---------------------------------------------------------------- retificação e máscaras


def homografia_mm(cantos_px: np.ndarray, dims_mm: tuple[float, float], px_por_mm_saida: float) -> np.ndarray:
    """Homografia imagem → retângulo da face (lado curto na horizontal)."""
    curto, longo = sorted(dims_mm)
    destino = np.array([[0, 0], [curto, 0], [curto, longo], [0, longo]], dtype=np.float64) * px_por_mm_saida
    return cv2.getPerspectiveTransform(cantos_px.astype(np.float32), destino.astype(np.float32))


def retificar(img: np.ndarray, cantos_px, dims_mm, px_por_mm_saida: float) -> np.ndarray:
    curto, longo = sorted(dims_mm)
    h = homografia_mm(cantos_px, dims_mm, px_por_mm_saida)
    tam = (round(curto * px_por_mm_saida), round(longo * px_por_mm_saida))
    return cv2.warpPerspective(img, h, tam, flags=cv2.INTER_LANCZOS4)


def px_para_mm(pontos_px: np.ndarray, cantos_px, dims_mm) -> np.ndarray:
    h = homografia_mm(cantos_px, dims_mm, 1.0)
    p = cv2.perspectiveTransform(np.asarray(pontos_px, np.float64).reshape(-1, 1, 2), h)
    return p.reshape(-1, 2)


def mascara_face(
    forma: tuple[int, int],
    cantos_px: np.ndarray,
    dims_mm: tuple[float, float],
    borda_mm: float = 0.0,
    raio_canto_mm: float = config.RAIO_CANTO_PADRAO_MM,
    px_mm: float = 10.0,
) -> np.ndarray:
    """Máscara (bool) da face com cantos arredondados, recuada `borda_mm` da borda."""
    curto, longo = sorted(dims_mm)
    s = px_mm
    m = np.zeros((round(longo * s), round(curto * s)), np.uint8)
    r = max(raio_canto_mm - borda_mm, 0.0) * s
    b = borda_mm * s
    x0, y0, x1, y1 = b, b, curto * s - b, longo * s - b
    cv2.rectangle(m, (round(x0 + r), round(y0)), (round(x1 - r), round(y1)), 1, cv2.FILLED)
    cv2.rectangle(m, (round(x0), round(y0 + r)), (round(x1), round(y1 - r)), 1, cv2.FILLED)
    if r > 0:
        for cx, cy in [(x0 + r, y0 + r), (x1 - r, y0 + r), (x1 - r, y1 - r), (x0 + r, y1 - r)]:
            cv2.circle(m, (round(cx), round(cy)), round(r), 1, cv2.FILLED)
    h_inv = np.linalg.inv(homografia_mm(cantos_px, dims_mm, s))
    saida = cv2.warpPerspective(m, h_inv, (forma[1], forma[0]), flags=cv2.INTER_NEAREST)
    return saida.astype(bool)


def distancia_borda_mm(mascara_sem_borda: np.ndarray, px_mm: float) -> np.ndarray:
    """Distância (mm) de cada pixel da máscara até fora dela."""
    return cv2.distanceTransform(mascara_sem_borda.astype(np.uint8), cv2.DIST_L2, 5) / px_mm


# ---------------------------------------------------------------- alinhamento


def alinhar(
    referencia: np.ndarray, img: np.ndarray, mascara: np.ndarray, limite_px: float = config.DESLOCAMENTO_MAX_PX
) -> tuple[np.ndarray, tuple[float, float]]:
    """Corrige translação de `img` em relação à `referencia` por correlação de fase
    sobre o gradiente (as luzes são diferentes; as bordas são as mesmas). Devolve o
    deslocamento medido, corrigido ou não."""
    ys, xs = np.nonzero(mascara)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1

    def grad(a):
        a = cv2.GaussianBlur(a[y0:y1, x0:x1].astype(np.float32), (0, 0), 2)
        gx = cv2.Sobel(a, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(a, cv2.CV_32F, 0, 1)
        g = cv2.magnitude(gx, gy)
        return g / (g.std() + 1e-6)

    ga, gb = grad(referencia), grad(img)
    janela = cv2.createHanningWindow(ga.shape[::-1], cv2.CV_32F)
    (dx, dy), _ = cv2.phaseCorrelate(ga, gb, janela)
    if max(abs(dx), abs(dy)) <= limite_px:  # guia 15.3 passo 8: corrigir só acima de 2 px
        return img, (float(dx), float(dy))
    m = np.float32([[1, 0, -dx], [0, 1, -dy]])
    corrigida = cv2.warpAffine(img, m, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return corrigida, (float(dx), float(dy))
