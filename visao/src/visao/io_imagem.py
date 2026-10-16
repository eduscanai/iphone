"""Leitura de HEIC, DNG e JPEG para numpy, ignorando a orientação EXIF (guia R21, 15.1).

HEIC: o libheif aplica as transformações do contêiner (irot/imir), que não são EXIF.
No app da cabine elas ficam fixas (`videoRotationAngle = 0`); nas fotos da fase 0,
tiradas com o app Câmera, a rotação é a mesma entre as fotos de uma face.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

FORMATOS = {
    ".heic": "heic",
    ".heif": "heic",
    ".dng": "dng",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
}

_PESOS_LUMINANCIA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


@dataclass
class Imagem:
    cinza: np.ndarray  # float32, 0 a 1, H × W
    cor: np.ndarray | None  # float32 RGB, 0 a 1, H × W × 3; só com `com_cor=True`
    formato: str
    bits: int
    caminho: Path

    @property
    def largura(self) -> int:
        return self.cinza.shape[1]

    @property
    def altura(self) -> int:
        return self.cinza.shape[0]


def formato_de(caminho: Path) -> str:
    try:
        return FORMATOS[caminho.suffix.lower()]
    except KeyError:
        raise ValueError(f"Formato não suportado: {caminho.name}") from None


def _bits(arr: np.ndarray) -> int:
    if arr.dtype == np.uint16:
        return 16
    if arr.dtype == np.uint8:
        return 8
    raise ValueError(f"Tipo de pixel inesperado: {arr.dtype}")


def _converter(arr: np.ndarray, com_cor: bool):
    """Inteiros → float32 0..1. O cinza é calculado canal a canal, sem montar a imagem
    em cor em float32: uma foto de 48 MP em cor ocupa ~580 MB."""
    bits = _bits(arr)
    escala = np.float32(1.0 / (2**bits - 1))
    if arr.ndim == 2:
        cinza = arr.astype(np.float32) * escala
        return cinza, (np.repeat(cinza[..., None], 3, axis=2) if com_cor else None), bits
    cinza = np.zeros(arr.shape[:2], np.float32)
    for c, peso in enumerate(_PESOS_LUMINANCIA):  # descarta alfa
        cinza += arr[..., c].astype(np.float32) * (peso * escala)
    cor = arr[..., :3].astype(np.float32) * escala if com_cor else None
    return cinza, cor, bits


def _ler_heic(caminho: Path) -> np.ndarray:
    import pillow_heif

    heif = pillow_heif.open_heif(caminho, convert_hdr_to_8bit=False)
    return np.asarray(heif)


def _ler_dng(caminho: Path) -> np.ndarray:
    import rawpy

    with rawpy.imread(str(caminho)) as raw:
        # user_flip=0: não gira pela orientação gravada no arquivo
        return raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=16, user_flip=0)


def _ler_pil(caminho) -> np.ndarray:
    from PIL import Image

    # Image.open não aplica a orientação EXIF; não chamar ImageOps.exif_transpose.
    with Image.open(caminho) as img:
        if img.mode in ("I;16", "I;16B", "I;16L"):
            return np.asarray(img, dtype=np.uint16)
        return np.asarray(img.convert("RGB"))


def ler_bytes(dados: bytes, formato: str, com_cor: bool = False) -> Imagem:
    """Lê a foto da memória (worker: fotos baixadas por URL)."""
    import io

    if formato == "heic":
        import pillow_heif

        arr = np.asarray(pillow_heif.open_heif(io.BytesIO(dados), convert_hdr_to_8bit=False))
    elif formato == "dng":
        import rawpy

        with rawpy.imread(io.BytesIO(dados)) as raw:
            arr = raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=16, user_flip=0)
    else:
        arr = _ler_pil(io.BytesIO(dados))
    cinza, cor, bits = _converter(arr, com_cor)
    return Imagem(cinza=cinza, cor=cor, formato=formato, bits=bits, caminho=Path("<memória>"))


def ler(caminho: str | Path, com_cor: bool = False) -> Imagem:
    """Lê a foto. Por padrão só o cinza (a detecção usa luminância, guia 15.1)."""
    caminho = Path(caminho)
    formato = formato_de(caminho)
    leitor = {"heic": _ler_heic, "dng": _ler_dng}.get(formato, _ler_pil)
    cinza, cor, bits = _converter(leitor(caminho), com_cor)
    return Imagem(cinza=cinza, cor=cor, formato=formato, bits=bits, caminho=caminho)


def para_u8(x: np.ndarray) -> np.ndarray:
    """float 0..1 → uint8."""
    return np.clip(x * 255.0 + 0.5, 0, 255).astype(np.uint8)


def esticar(x: np.ndarray, mascara: np.ndarray | None = None, p_baixo=1.0, p_alto=99.7) -> np.ndarray:
    """Estica o contraste por percentis (para imagens de conferência)."""
    v = x[mascara] if mascara is not None and mascara.any() else x
    lo, hi = np.percentile(v, [p_baixo, p_alto])
    return np.clip((x - lo) / max(hi - lo, 1e-6), 0, 1).astype(np.float32)
