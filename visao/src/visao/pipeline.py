"""Processamento de uma foto e fusão de uma sessão (guia 15; contratos 7.6 e 7.9).

A visão devolve defeitos medidos em mm; quem decide a nota é o backend (R13).
Cada foto é retificada a R = máx(R da tarefa, px/mm nativo) e a camada (a) roda no espaço
retificado: como R ≥ resolução nativa, nada se perde (R4), e as medidas saem direto em mm
no referencial da face (7.2).
"""

import math
import time
from collections.abc import Callable

import cv2
import numpy as np

from . import anotar, config, geometria, zonas
from . import riscos as camada_a
from .io_imagem import ler_bytes

Baixar = Callable[[str], bytes]
Enviar = Callable[[str, bytes], None]

DIRECOES = {"topo_para_cima": (0, -1), "topo_para_baixo": (0, 1), "topo_para_esquerda": (-1, 0),
            "topo_para_direita": (1, 0)}
T_TELA_ACESA = 0.35  # luminância média da tela (0 a 1) acima disso = tela acesa


def _tipo_luz(luz: str) -> str:
    return "rasante" if luz.startswith("rasante") else luz


def confianca_risco(contraste: float) -> float:
    """Heurística até calibrar com as marcações dos técnicos: logística no contraste (em MADs)."""
    return round(1 / (1 + math.exp(-(contraste - 12) / 4)), 3)


# ---------------------------------------------------------------- geometria e orientação


def orientar_topo(cantos: np.ndarray, orientacao: str | None) -> np.ndarray:
    """Põe o lado do topo como lado 0→1 (y = 0 na face retificada), pela posição do batente."""
    if orientacao not in DIRECOES:
        return cantos
    d = np.array(DIRECOES[orientacao], float)
    centro = cantos.mean(axis=0)
    lado01 = (cantos[0] + cantos[1]) / 2 - centro
    lado23 = (cantos[2] + cantos[3]) / 2 - centro
    return cantos if np.dot(lado01, d) >= np.dot(lado23, d) else np.roll(cantos, -2, axis=0)


def textura(img: np.ndarray) -> float:
    g = cv2.GaussianBlur(img, (0, 0), 2)
    return float(cv2.Laplacian(g, cv2.CV_32F).var())


def conferir_ilha_camera(ret: np.ndarray) -> str:
    """Traseira: a ilha de câmeras fica perto da origem (canto superior esquerdo, guia 7.2).
    Devolve 'ok', 'girar' (está no canto oposto) ou 'indefinido'."""
    h, w = ret.shape
    lado = int(min(h, w) * 0.45)
    origem, oposto = textura(ret[:lado, :lado]), textura(ret[h - lado:, w - lado:])
    if origem > 1.5 * oposto:
        return "ok"
    if oposto > 1.5 * origem:
        return "girar"
    return "indefinido"


class FaceGeom:
    def __init__(self, face, cantos, dims_wh, r, aparelho: geometria.Aparelho | None, orientacao_ok):
        self.face, self.cantos, self.dims_wh, self.r = face, cantos, dims_wh, r
        self.aparelho, self.orientacao_ok = aparelho, orientacao_ok

    def homografia(self) -> np.ndarray:
        return geometria.homografia_mm(self.cantos, self.dims_wh, 1.0)  # imagem → mm

    def retificar(self, img: np.ndarray) -> np.ndarray:
        ret = geometria.retificar(img, self.cantos, self.dims_wh, self.r)
        w, h = self.dims_wh
        if w > h:  # topo e base: a retificação sai em retrato; a face é paisagem
            ret = cv2.rotate(ret, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return ret

    def como_dict(self) -> dict:
        ap = self.aparelho
        return {
            "face": self.face,
            "cantos_px": np.round(self.cantos, 2).tolist(),
            "homografia": self.homografia().tolist(),
            "mm_por_px": round(1 / ap.px_por_mm, 5) if ap else None,
            "residuo_bordas_mm": round(ap.residuo_bordas_mm, 3) if ap else None,
            "orientacao_ok": self.orientacao_ok,
        }


def geometria_principal(img, face, aparelho, perfil, pose, r_alvo) -> tuple[FaceGeom | None, str | None]:
    w_mm, h_mm = zonas.dims_da_face(face, aparelho["dimensoes_mm"])
    raio = aparelho.get("raio_canto_mm") or config.RAIO_CANTO_PADRAO_MM
    px_hint = perfil.get("px_por_mm_berco") if pose == "deitado" else None
    ap = geometria.encontrar_aparelho(img, (w_mm, h_mm), px_hint, raio_canto_mm=raio)
    if ap is None:
        return None, "contorno não encontrado"
    if ap.fora_do_quadro:
        return None, "aparelho fora do quadro"
    orientacao = (perfil.get("orientacao") or {}).get(pose)
    cantos = orientar_topo(ap.cantos, orientacao)
    r = max(float(r_alvo), math.ceil(ap.px_por_mm))
    fg = FaceGeom(face, cantos, (w_mm, h_mm), r, ap, True if orientacao in DIRECOES else None)
    if face == "traseira":
        veredito = conferir_ilha_camera(fg.retificar(img))
        if veredito == "girar":
            fg.cantos = np.roll(cantos, -2, axis=0)
            fg.orientacao_ok = True
        elif veredito == "ok":
            fg.orientacao_ok = True
        elif fg.orientacao_ok is None:
            fg.orientacao_ok = False
    return fg, None


def geometria_espelhos(img, faces, aparelho, perfil, r) -> list[FaceGeom]:
    """Bordas refletidas nos espelhos a 45° (D3). A orientação dentro do espelho ainda não é
    conferida: orientacao_ok = None até validar com a cabine montada."""
    out = []
    regioes = perfil.get("regioes_espelho_px") or {}
    raio = aparelho.get("raio_canto_mm") or config.RAIO_CANTO_PADRAO_MM
    for face in faces:
        poli = np.array(regioes.get(face) or [], float)
        if poli.shape != (4, 2) or not np.ptp(poli, axis=0).all():
            continue
        x0, y0 = np.floor(poli.min(axis=0)).astype(int).clip(0)
        x1, y1 = np.ceil(poli.max(axis=0)).astype(int)
        recorte = img[y0:y1, x0:x1]
        w_mm, h_mm = zonas.dims_da_face(face, aparelho["dimensoes_mm"])
        ap = geometria.encontrar_aparelho(recorte, (w_mm, h_mm), None, raio_canto_mm=min(raio, min(w_mm, h_mm) / 2))
        if ap is None or ap.fora_do_quadro:
            continue
        ap.cantos = ap.cantos + [x0, y0]
        out.append(FaceGeom(face, ap.cantos, (w_mm, h_mm), r, ap, None))
    return out


# ---------------------------------------------------------------- qualidade


def faixa_da_borda(mascara: np.ndarray, px_mm: float, mm: float = 1.0) -> np.ndarray:
    fora = cv2.distanceTransform((~mascara).astype(np.uint8), cv2.DIST_L2, 3)
    dentro = cv2.distanceTransform(mascara.astype(np.uint8), cv2.DIST_L2, 3)
    return np.maximum(fora, dentro) <= mm * px_mm


def qualidade(img: np.ndarray, mascara: np.ndarray, luz: str, px_mm: float) -> dict:
    """Nitidez medida na faixa de ±1 mm do contorno: a tela apagada é lisa mesmo com a foto
    nítida, então a variância do Laplaciano dentro do aparelho não serve (guia 14.6, ajustado)."""
    v = img[mascara]
    faixa = faixa_da_borda(mascara, px_mm)
    g = img * 255
    lap = cv2.Laplacian(g, cv2.CV_32F)[faixa]
    grad2 = (cv2.Sobel(g, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(g, cv2.CV_32F, 0, 1) ** 2)[faixa]
    # normalizada pela energia do gradiente: não depende do contraste da borda (cor do aparelho, luz)
    nitidez = float(lap.var() / (grad2.mean() + 1e-6) * 100)
    estouro = float(np.mean(v >= 250 / 255) * 100)
    q = {"ok": True, "nitidez": round(nitidez, 1), "estouro_pct": round(estouro, 3), "contorno_ok": True, "motivo": None}
    if nitidez < config.T_NITIDEZ:
        q.update(ok=False, motivo="tremida")
    elif estouro > config.ESTOURO_MAX_PCT[_tipo_luz(luz)]:
        q.update(ok=False, motivo="estourada")
    return q


# ---------------------------------------------------------------- foto


def processar_foto(t: dict, baixar: Baixar, enviar: Enviar | None = None, modelos=None) -> dict:
    """Tarefa `foto` → resultado (7.9). Imagem ilegível ou sem contorno = qualidade.ok False.
    `modelos` (visao.modelos.Modelos): camadas (b) e (c) na foto ambiente, se carregadas."""
    t0 = time.monotonic()
    foto, ap_info = t["foto"], t["aparelho"]
    perfil = t.get("perfil_calibracao") or {}
    r_alvo = t.get("config", {}).get("px_por_mm_retificacao", 20)
    base = {"tarefa_id": t["tarefa_id"], "tipo": "foto", "foto_id": foto["foto_id"], "versao_visao": config.VERSAO_PIPELINE,
            "faces_extraidas": [], "deteccoes": [], "artefatos": {"retificada": False, "anotada": False}}

    def reprovar(motivo, **extra):
        return base | {"qualidade": {"ok": False, "motivo": motivo, "contorno_ok": motivo != "contorno não encontrado",
                                     **extra}, "tempo_ms": int((time.monotonic() - t0) * 1000)}

    try:
        img = ler_bytes(baixar(foto["url"]), foto["formato"]).cinza
    except (OSError, ValueError) as e:
        return reprovar(f"imagem ilegível: {type(e).__name__}")

    fg, motivo = geometria_principal(img, foto["face"], ap_info, perfil, foto["pose"], r_alvo)
    if fg is None:
        return reprovar(motivo)
    mascara = geometria.mascara_face(img.shape, fg.cantos, fg.dims_wh, 0.0,
                                     ap_info.get("raio_canto_mm") or config.RAIO_CANTO_PADRAO_MM, fg.aparelho.px_por_mm)
    q = qualidade(img, mascara, foto["luz"], fg.aparelho.px_por_mm)
    ret = fg.retificar(img)
    rot = zonas.mapa(foto["face"], ap_info["dimensoes_mm"], ap_info.get("raio_canto_mm") or 0,
                     ap_info.get("zonas_mm") or {}, fg.r)
    if q["ok"] and foto["luz"] == "ambiente" and foto["face"] == "frente":
        tela = rot == zonas.PRIORIDADE.index("tela")
        if tela.any() and float(ret[tela].mean()) > T_TELA_ACESA:
            q.update(ok=False, motivo="tela acesa")
    faces = [fg] + geometria_espelhos(img, foto.get("faces", [])[1:], ap_info, perfil, fg.r)

    deteccoes = []
    if foto["luz"].startswith("rasante") and q["ok"]:
        irma = next((i for i in t.get("fotos_irmas", []) if i["luz"] == "ambiente"), None)
        ret_amb = None
        if irma is not None:
            img_amb = ler_bytes(baixar(irma["url"]), irma.get("formato", foto["formato"])).cinza
            fg_amb, _ = geometria_principal(img_amb, foto["face"], ap_info, perfil, foto["pose"], fg.r)
            if fg_amb is not None:
                # cada foto tem a sua homografia (15.3 passo 8), mas a mesma orientação da rasante
                girada = np.roll(fg_amb.cantos, -2, axis=0)
                if np.abs(girada - fg.cantos).sum() < np.abs(fg_amb.cantos - fg.cantos).sum():
                    fg_amb.cantos = girada
                fg_amb.r = fg.r
                ret_amb = fg_amb.retificar(img_amb)
                del img_amb
        deteccoes = detectar_riscos(foto["face"], ret, ret_amb, rot, fg.r)

    if modelos is not None and foto["luz"] == "ambiente" and q["ok"]:
        from . import anomalia, detector

        for f in faces:
            r_img = ret if f is fg else f.retificar(img)
            rot_f = rot if f is fg else zonas.mapa(f.face, ap_info["dimensoes_mm"], ap_info.get("raio_canto_mm") or 0,
                                                    ap_info.get("zonas_mm") or {}, fg.r)
            deteccoes += detector.detectar(modelos, f.face, r_img, rot_f, fg.r)
            anom, _ = anomalia.detectar(modelos, f.face, ap_info.get("familia") or {}, r_img, rot_f, fg.r)
            deteccoes += anom

    artefatos = {"retificada": False, "anotada": False}
    if enviar is not None:
        up = t.get("upload") or {}
        for f in faces:
            r_img = ret if f is fg else f.retificar(img)
            if url := (up.get("retificada") or {}).get(f.face):
                enviar(url, anotar.jpeg(r_img))
                artefatos["retificada"] = True
            if url := (up.get("anotada") or {}).get(f.face):
                enviar(url, anotar.anotada(r_img, [d for d in deteccoes if d["face"] == f.face], fg.r))
                artefatos["anotada"] = True
    return base | {
        "qualidade": q,
        "faces_extraidas": [f.como_dict() for f in faces],
        "deteccoes": deteccoes,
        "artefatos": artefatos,
        "tempo_ms": int((time.monotonic() - t0) * 1000),
    }


def detectar_riscos(face: str, ret: np.ndarray, ret_amb: np.ndarray | None, rot: np.ndarray, r: float) -> list[dict]:
    """Camada (a) na face retificada, só no interior (tela ou vidro traseiro)."""
    if face not in zonas.INTERIOR:
        return []
    h = min(ret.shape[0], rot.shape[0], ret_amb.shape[0] if ret_amb is not None else 10**9)
    w = min(ret.shape[1], rot.shape[1], ret_amb.shape[1] if ret_amb is not None else 10**9)
    ret, rot = ret[:h, :w], rot[:h, :w]
    amb = ret_amb[:h, :w] if ret_amb is not None else None
    # só vidro (guia 15.4): quina e moldura ficam de fora (o friso da moldura brilha na rasante)
    vidro = [zonas.PRIORIDADE.index(z) for z in ("tela", "recorte_tela", "vidro_traseiro", "ilha_camera", "lente_camera")]
    interior = np.isin(rot, vidro)
    faixa = int(np.ceil(config.PARAM_RISCOS.faixa_busca_mm * r))
    interior[:faixa], interior[-faixa:], interior[:, :faixa], interior[:, -faixa:] = False, False, False, False
    det = camada_a.detectar(ret, amb, interior, r)
    realce_amb = camada_a.Realce.de(amb, interior, r, det.recorte) if amb is not None else None
    out = []
    for risco in det.riscos:
        pts_mm = risco.caminho_px / r
        x, y, ww, hh = (np.array(risco.caixa_px) / r).tolist()
        c_amb = realce_amb.contraste(risco) if realce_amb else None
        out.append({
            "face": face, "fonte": "opencv_riscos", "tipo": "risco", "zona": zonas.zona_de(rot, risco.esqueleto_px),
            "geometria_mm": {"tipo": "polilinha", "pontos": np.round(pts_mm, 2).tolist()},
            "caixa_mm": [round(x, 2), round(y, 2), round(ww, 2), round(hh, 2)],
            "comprimento_mm": risco.comprimento_mm, "contraste_rasante": risco.contraste,
            "contraste_ambiente": c_amb, "confianca": confianca_risco(risco.contraste),
        })
    return out
