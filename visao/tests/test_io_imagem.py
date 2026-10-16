import numpy as np
from PIL import Image

from visao.io_imagem import ler


def test_jpeg_ignora_orientacao_exif(tmp_path):
    arr = np.zeros((40, 80, 3), np.uint8)
    arr[:, :40] = 255
    img = Image.fromarray(arr)
    exif = Image.Exif()
    exif[0x0112] = 6  # girar 90°
    caminho = tmp_path / "foto.jpg"
    img.save(caminho, exif=exif, quality=95)
    lida = ler(caminho)
    assert lida.cinza.shape == (40, 80)
    assert lida.cinza.dtype == np.float32
    assert lida.cinza[:, :30].mean() > 0.9 and lida.cinza[:, 50:].mean() < 0.1


def test_heic_16_bits(tmp_path):
    import pillow_heif

    arr = (np.linspace(0, 65535, 64 * 64 * 3).reshape(64, 64, 3)).astype(np.uint16)
    caminho = tmp_path / "foto.heic"
    try:
        pillow_heif.from_bytes(mode="RGB;16", size=(64, 64), data=arr.tobytes()).save(caminho, quality=-1)
    except Exception:  # codificador indisponível nesta máquina
        import pytest

        pytest.skip("sem codificador HEIC")
    lida = ler(caminho)
    assert lida.cinza.shape == (64, 64)
    assert 0 <= lida.cinza.min() and lida.cinza.max() <= 1
