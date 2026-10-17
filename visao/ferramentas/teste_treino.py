"""Teste de fumaça da cadeia de treino do detector (camada c), com dados sintéticos:

    exportar_dataset.montar → treinar_detector.py → modelos.carregar → detector.detectar

Não mede qualidade (poucas épocas): mostra que tudo funciona com as versões instaladas.

    uv run --extra treino python -I ferramentas/teste_treino.py <pasta_de_trabalho> [--epocas 2]
"""

import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import exportar_dataset as exp  # noqa: E402

R, W, H = 10.0, 72, 147


def face_sintetica(rng):
    img = (np.full((int(H * R), int(W * R)), 25) + rng.normal(0, 3, (int(H * R), int(W * R)))).clip(0, 255).astype(np.uint8)
    defeitos = []
    for _ in range(rng.integers(2, 5)):
        x, y = rng.uniform(8, W - 25), rng.uniform(8, H - 25)
        if rng.random() < 0.6:  # risco: linha fina clara
            comp, ang = rng.uniform(8, 18), rng.uniform(0, np.pi)
            x1, y1 = x + comp * np.cos(ang), y + comp * np.sin(ang)
            cv2.line(img, (int(x * R), int(y * R)), (int(x1 * R), int(y1 * R)), 200, 2, cv2.LINE_AA)
            tipo, x0, y0 = "risco", min(x, x1), min(y, y1)
            w, h = abs(x1 - x), abs(y1 - y)
        else:  # trinca: zigue-zague grosso
            pts = [(x, y)]
            for _ in range(6):
                pts.append((pts[-1][0] + rng.uniform(1, 3), pts[-1][1] + rng.uniform(-2, 2)))
            cv2.polylines(img, [(np.array(pts) * R).astype(np.int32)], False, 255, 4, cv2.LINE_AA)
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            tipo, x0, y0, w, h = "trinca", min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        defeitos.append({"tipo": tipo, "caixa_mm": [x0 - 1, y0 - 1, w + 2, h + 2]})
    return np.repeat(img[..., None], 3, axis=2), defeitos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta", type=Path)
    ap.add_argument("--epocas", type=int, default=2)
    ap.add_argument("--dispositivo", default="mps")
    ap.add_argument("--rapido", action="store_true",
                    help="6 faces, resolução 320, CPU: só prova que a cadeia funciona (Mac de 8 GB)")
    args = ap.parse_args()
    rng = np.random.default_rng(0)
    sessoes, imagens, rs = {}, {}, {}
    n = 6 if args.rapido else 30
    if args.rapido:
        args.epocas, args.dispositivo = 1, "cpu"
    for i in range(n):
        conjunto = "treino" if i < n * 2 // 3 else ("validacao" if i < n * 5 // 6 else "teste")
        img, defeitos = face_sintetica(rng)
        sid = f"s{i:03d}-sintetica"
        sessoes[sid] = {"conjunto": conjunto, "faces": {"frente": {"positivos": defeitos, "rejeitados": []}}}
        imagens[(sid, "frente")], rs[(sid, "frente")] = img, R
    print("dataset:", exp.montar(sessoes, imagens, rs, args.pasta / "coco"))

    destino = args.pasta / "modelos"
    subprocess.run([sys.executable, "-I", str(AQUI / "treinar_detector.py"), "--dataset", str(args.pasta / "coco"),
                    "--versao", "rfdetr-s-teste-sintetico", "--epocas", str(args.epocas), "--lote", "2",
                    "--acumular", "1", "--dispositivo", args.dispositivo, "--destino", str(destino / "detector"),
                    "--sem-registro"] + (["--resolucao", "320"] if args.rapido else []), check=True)

    from visao import detector, modelos, zonas

    m = modelos.carregar(destino, args.dispositivo)
    assert m.detector is not None, "detector não carregou"
    img, _ = face_sintetica(np.random.default_rng(99))
    ret = img[..., 0].astype(np.float32) / 255
    rot = zonas.mapa("frente", {"largura": W, "altura": H, "espessura": 7.65}, 9.0, {}, R)[: ret.shape[0], : ret.shape[1]]
    achados = detector.detectar(m, "frente", ret, rot, R)
    print(f"OK: modelo {m.versao_detector} carregado; {len(achados)} detecções numa face nova "
          "(com poucas épocas o número não importa)")


if __name__ == "__main__":
    main()
