"""Apoio aos protótipos da fase 0 (guia, seção 8): catálogo das fotos, dimensões dos
modelos, anotação do técnico, análise de uma face e imagens de conferência."""

import csv
import hashlib
import os
import pickle
import re
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import config, geometria
from . import riscos as camada_a
from .io_imagem import FORMATOS, esticar, ler, para_u8

RAIZ = Path(__file__).resolve().parents[2]  # visao/
# As variáveis de ambiente servem para rodar com outro conjunto de fotos (ex.: sintético).
DIR_FOTOS = Path(os.environ.get("VISAO_FASE0_FOTOS", RAIZ / "prototipos" / "fotos"))
DIR_SAIDA = Path(os.environ.get("VISAO_FASE0_SAIDA", RAIZ / "prototipos" / "saida"))
DIR_DOCS = Path(os.environ.get("VISAO_FASE0_DOCS", RAIZ.parent / "docs"))

# Dimensões externas (largura, altura, espessura) em mm, das páginas de especificações
# técnicas da Apple. VERIFICAR antes de usar fora da fase 0; o cadastro oficial fica
# em backend/app/estetica/dimensoes.py (guia, Apêndice A).
DIMENSOES_MM = {
    "iphone xr": (75.7, 150.9, 8.3),
    "iphone 11": (75.7, 150.9, 8.3),
    "iphone 11 pro": (71.4, 144.0, 8.1),
    "iphone 11 pro max": (77.8, 158.0, 8.1),
    "iphone se 2": (67.3, 138.4, 7.3),
    "iphone se 3": (67.3, 138.4, 7.3),
    "iphone 12 mini": (64.2, 131.5, 7.4),
    "iphone 12": (71.5, 146.7, 7.4),
    "iphone 12 pro": (71.5, 146.7, 7.4),
    "iphone 12 pro max": (78.1, 160.8, 7.4),
    "iphone 13 mini": (64.2, 131.5, 7.65),
    "iphone 13": (71.5, 146.7, 7.65),
    "iphone 13 pro": (71.5, 146.7, 7.65),
    "iphone 13 pro max": (78.1, 160.8, 7.65),
    "iphone 14": (71.5, 146.7, 7.8),
    "iphone 14 plus": (78.1, 160.8, 7.8),
    "iphone 14 pro": (71.5, 147.5, 7.85),
    "iphone 14 pro max": (77.6, 160.7, 7.85),
    "iphone 15": (71.6, 147.6, 7.8),
    "iphone 15 plus": (77.8, 160.9, 7.8),
    "iphone 15 pro": (70.6, 146.6, 8.25),
    "iphone 15 pro max": (76.7, 159.9, 8.25),
    "iphone 16": (71.6, 147.6, 7.8),
    "iphone 16 plus": (77.8, 160.9, 7.8),
    "iphone 16 pro": (71.5, 149.6, 8.25),
    "iphone 16 pro max": (77.6, 163.0, 8.25),
}

# Luzes nos nomes de arquivo da fase 0 (guia 8.2 passo 9) → enum Luz (guia 7.1)
LUZES = {"amb": "ambiente", "ra": "rasante_a", "rb": "rasante_b", "sil": "contraluz"}
PREFERENCIA_FORMATO = ["dng", "heic", "jpeg", "png"]

_PADRAO = re.compile(r"^ap(?P<n>\d+)_(?P<resto>.+)$", re.IGNORECASE)


# ---------------------------------------------------------------- catálogo


@dataclass(frozen=True)
class Foto:
    aparelho: int
    face: str  # frente, traseira, lat, foco, espelho, sujo
    luz: str  # amb, ra, rb, sil, lateral, ponta
    caminho: Path

    @property
    def formato(self) -> str:
        return FORMATOS[self.caminho.suffix.lower()]


def catalogo(pasta: Path = DIR_FOTOS) -> dict[tuple[int, str, str], Foto]:
    """(aparelho, face, luz) → Foto. Com dois formatos da mesma foto, prefere DNG."""
    achadas: dict[tuple[int, str, str], list[Foto]] = {}
    for p in sorted(pasta.glob("*")):
        if p.suffix.lower() not in FORMATOS:
            continue
        m = _PADRAO.match(p.stem)
        if not m or "_" not in m["resto"]:
            print(f"aviso: nome fora do padrão ap{{n}}_{{face}}_{{luz}}: {p.name}")
            continue
        face, luz = m["resto"].lower().rsplit("_", 1)
        f = Foto(int(m["n"]), face, luz, p)
        achadas.setdefault((f.aparelho, face, luz), []).append(f)
    return {k: min(v, key=lambda f: PREFERENCIA_FORMATO.index(f.formato)) for k, v in achadas.items()}


def aparelhos(cat) -> list[int]:
    return sorted({k[0] for k in cat})


# ---------------------------------------------------------------- anotação e modelos


@dataclass
class Anotacao:
    linhas: list[dict] = field(default_factory=list)

    def do_aparelho(self, n: int) -> list[dict]:
        return [l for l in self.linhas if _num(l.get("aparelho", "")) == n]

    def modelo(self, n: int) -> str | None:
        for l in self.do_aparelho(n):
            if l.get("modelo"):
                return l["modelo"].strip()
        return None


def _num(texto: str) -> int | None:
    m = re.search(r"\d+", texto or "")
    return int(m.group()) if m else None


def ler_anotacao(caminho: Path = DIR_FOTOS / "anotacao.csv") -> Anotacao:
    if not caminho.exists():
        print(f"aviso: {caminho} não encontrado; sem anotação do técnico")
        return Anotacao()
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        return Anotacao([{k.strip(): (v or "").strip() for k, v in l.items()} for l in csv.DictReader(f)])


def dimensoes_modelo(nome: str | None) -> tuple[float, float, float]:
    if not nome:
        raise ValueError("Modelo não informado em anotacao.csv")
    chave = re.sub(r"\s+", " ", nome.lower().replace("(", "").replace(")", "")).strip()
    chave = chave.replace("ª geração", "").replace("a geração", "").replace("geração", "").strip()
    chave = re.sub(r"se (\d)", r"se \1", chave)
    if chave not in DIMENSOES_MM:
        raise ValueError(f"Modelo '{nome}' sem dimensões em visao/src/visao/fase0.py (DIMENSOES_MM)")
    return DIMENSOES_MM[chave]


def dims_da_foto(face: str, luz: str, dims: tuple[float, float, float]) -> tuple[float, float]:
    """(lado curto, lado longo) da face visível de cima em cada foto da fase 0."""
    larg, alt, esp = dims
    if face == "lat" or (face == "foco" and luz == "lateral"):
        return (esp, alt)
    if face == "foco" and luz == "ponta":
        return (esp, larg)
    return (larg, alt)  # frente, traseira, espelho (aparelho deitado), sujo


def altura_da_face_mm(face: str, luz: str, dims: tuple[float, float, float]) -> float:
    """Altura (mm) da face fotografada acima da mesa."""
    larg, alt, esp = dims
    if face == "lat" or (face == "foco" and luz == "lateral"):
        return larg
    if face == "foco" and luz == "ponta":
        return alt
    return esp


def escala_para_busca(px_aruco: float | None, face: str, luz: str, dims) -> float | None:
    """Escala dos ArUco (na mesa) só serve para conferir a área de faces perto da mesa.
    Em pé, a face fica 70–150 mm mais perto da câmera e aparece até ~2× maior."""
    return px_aruco if px_aruco and altura_da_face_mm(face, luz, dims) < 20 else None


# ---------------------------------------------------------------- análise de uma face


@dataclass
class AnaliseFace:
    aparelho: int
    face: str
    forma: tuple[int, int]
    dims_mm: tuple[float, float]
    px_mm: float
    cantos: np.ndarray
    fonte_contorno: str
    residuo_bordas_mm: float
    deslocamentos: dict[str, tuple[float, float]]
    riscos: dict[str, list[camada_a.Risco]]  # ra, rb, uniao
    contraste_ambiente: dict[str, list[float]]
    perto_borda: dict[str, list[bool]]
    mascara_borda_mm: float


def _chave_cache(fotos: list[Foto], extra: str) -> str:
    h = hashlib.sha256(extra.encode())
    for f in fotos:
        st = f.caminho.stat()
        h.update(f"{f.caminho.name}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()[:16]


def analisar_face(cat, n: int, face: str, dims: tuple[float, float, float], usar_cache=True) -> AnaliseFace | None:
    """Contorno pela `amb` (e `sil`, se houver), alinhamento e camada (a) em `ra`, `rb`
    e na união das duas. Resultado em cache em saida/cache/."""
    amb = cat.get((n, face, "amb"))
    if amb is None:
        return None
    rasantes = {l: cat[(n, face, l)] for l in ("ra", "rb") if (n, face, l) in cat}
    if not rasantes:
        return None
    sil = cat.get((n, face, "sil"))
    fotos = [amb, *rasantes.values(), *([sil] if sil else [])]
    p = config.PARAM_RISCOS
    chave = _chave_cache(fotos, repr(p) + repr(dims) + "v1")
    cache = DIR_SAIDA / "cache" / f"ap{n}_{face}_{chave}.pkl"
    if usar_cache and cache.exists():
        return pickle.loads(cache.read_bytes())

    dims_f = dims_da_foto(face, "amb", dims)
    img_amb = ler(amb.caminho).cinza
    img_sil = ler(sil.caminho).cinza if sil else None
    px_aruco = geometria.px_por_mm_aruco(geometria.detectar_aruco(img_amb))
    ap = geometria.encontrar_aparelho(img_amb, dims_f, px_aruco, silhueta=img_sil)
    if ap is None and img_sil is not None:
        ap = geometria.encontrar_aparelho(img_amb, dims_f, px_aruco)
    if ap is None:
        print(f"ap{n} {face}: contorno não encontrado")
        return None

    mascara = geometria.mascara_face(img_amb.shape, ap.cantos, dims_f, p.borda_excluida_mm, px_mm=ap.px_por_mm)
    dist_borda = geometria.distancia_borda_mm(
        geometria.mascara_face(img_amb.shape, ap.cantos, dims_f, 0.0, px_mm=ap.px_por_mm), ap.px_por_mm
    )

    deteccoes, deslocamentos = {}, {}
    for luz, foto in rasantes.items():
        img, desloc = geometria.alinhar(img_amb, ler(foto.caminho).cinza, mascara)
        deslocamentos[luz] = desloc
        deteccoes[luz] = camada_a.detectar(img, img_amb, mascara, ap.px_por_mm)
    resultado = {luz: d.riscos for luz, d in deteccoes.items()}
    if len(deteccoes) == 2:
        a, b = deteccoes["ra"], deteccoes["rb"]
        resultado["uniao"] = camada_a.detectar_binario(
            a.binario | b.binario, np.maximum(a.th, b.th), mascara, ap.px_por_mm, a.recorte
        )

    recorte = next(iter(deteccoes.values())).recorte
    realce_amb = camada_a.Realce.de(img_amb, mascara, ap.px_por_mm, recorte)
    contraste_amb = {l: [realce_amb.contraste(r) for r in rs] for l, rs in resultado.items()}
    perto = {
        l: [bool(dist_borda[r.esqueleto_px[:, 1], r.esqueleto_px[:, 0]].min() < p.perto_borda_mm) for r in rs]
        for l, rs in resultado.items()
    }
    analise = AnaliseFace(
        aparelho=n,
        face=face,
        forma=img_amb.shape,
        dims_mm=dims_f,
        px_mm=ap.px_por_mm,
        cantos=ap.cantos,
        fonte_contorno=ap.fonte,
        residuo_bordas_mm=ap.residuo_bordas_mm,
        deslocamentos=deslocamentos,
        riscos=resultado,
        contraste_ambiente=contraste_amb,
        perto_borda=perto,
        mascara_borda_mm=p.borda_excluida_mm,
    )
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps(analise))
    return analise


def coincide(risco: camada_a.Risco, outros: list[camada_a.Risco], forma, px_mm, tolerancia_mm=1.0) -> bool:
    """O risco aparece também em `outros`? (≥ 50% do esqueleto a até 1 mm de algum deles)."""
    if not outros:
        return False
    x0, y0, w, h = risco.caixa_px
    m = int(tolerancia_mm * px_mm) + 2
    ys, ye, xs, xe = max(y0 - m, 0), min(y0 + h + m, forma[0]), max(x0 - m, 0), min(x0 + w + m, forma[1])
    alvo = np.zeros((ye - ys, xe - xs), np.uint8)
    for o in outros:
        ox, oy, ow, oh = o.caixa_px
        if ox > xe or oy > ye or ox + ow < xs or oy + oh < ys:
            continue
        p = o.esqueleto_px - [xs, ys]
        dentro = (p[:, 0] >= 0) & (p[:, 0] < alvo.shape[1]) & (p[:, 1] >= 0) & (p[:, 1] < alvo.shape[0])
        alvo[p[dentro, 1], p[dentro, 0]] = 1
    if not alvo.any():
        return False
    k = int(round(tolerancia_mm * px_mm)) * 2 + 1
    alvo = cv2.dilate(alvo, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    p = risco.esqueleto_px - [xs, ys]
    return bool(alvo[p[:, 1], p[:, 0]].mean() >= 0.5)


# ---------------------------------------------------------------- imagens de conferência

CORES = {  # BGR
    "ra": (60, 60, 255),
    "rb": (255, 200, 60),
    "ambos": (60, 230, 255),
    "uniao": (60, 230, 255),
    "perdido": (255, 60, 255),
    "contorno": (80, 255, 80),
    "aruco": (255, 160, 0),
}


def base_conferencia(cinza: np.ndarray, mascara=None) -> np.ndarray:
    return cv2.cvtColor(para_u8(esticar(cinza, mascara)), cv2.COLOR_GRAY2BGR)


def desenhar_riscos(img_bgr, riscos, cor, espessura=3, rotulo=True, px_mm=None):
    for r in riscos:
        pts = np.round(r.caminho_px).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img_bgr, [pts], False, cor, espessura, cv2.LINE_AA)
        if rotulo:
            x, y, _, _ = r.caixa_px
            texto = f"{r.comprimento_mm:.1f}"
            esc = max(img_bgr.shape[1] / 3000, 0.6)
            cv2.putText(img_bgr, texto, (x, max(y - 6, 12)), cv2.FONT_HERSHEY_SIMPLEX, esc, cor, max(1, int(esc * 2)), cv2.LINE_AA)
    return img_bgr


def desenhar_cantos(img_bgr, cantos, cor=CORES["contorno"]):
    pts = np.round(cantos).astype(np.int32).reshape(-1, 1, 2)
    cv2.polylines(img_bgr, [pts], True, cor, max(2, img_bgr.shape[1] // 1500), cv2.LINE_AA)
    return img_bgr


def salvar(img_bgr: np.ndarray, caminho: Path, lado_max: int | None = 3000, qualidade=88):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    h, w = img_bgr.shape[:2]
    if lado_max and max(h, w) > lado_max:
        f = lado_max / max(h, w)
        img_bgr = cv2.resize(img_bgr, (round(w * f), round(h * f)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(caminho), img_bgr, [cv2.IMWRITE_JPEG_QUALITY, qualidade])
    return caminho


def recorte_1x1(img_bgr, centro_xy, lado=600):
    x, y = (int(round(v)) for v in centro_xy)
    h, w = img_bgr.shape[:2]
    x0, y0 = max(min(x - lado // 2, w - lado), 0), max(min(y - lado // 2, h - lado), 0)
    return img_bgr[y0 : y0 + lado, x0 : x0 + lado].copy()


def escrever_csv(caminho: Path, linhas: list[dict]):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not linhas:
        caminho.write_text("", encoding="utf-8")
        return caminho
    campos = list(dict.fromkeys(k for l in linhas for k in l))
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    return caminho


def ler_csv(caminho: Path) -> list[dict]:
    if not caminho.exists() or caminho.stat().st_size == 0:
        return []
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
