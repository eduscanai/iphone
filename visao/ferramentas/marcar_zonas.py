"""Ferramenta do humano para medir as zonas de um modelo (guia, Apêndice A, passo 2).

    uv run python -I ferramentas/marcar_zonas.py retificada.jpg --face traseira --largura 71.5

Abre a face retificada (de um aparelho nota A). Arraste para desenhar um retângulo; teclas:
  1 ilha_camera · 2 lente_camera · 3 recorte_tela · 4 botao · 5 porta · u desfaz · s salva · q sai
Saída: JSON em mm, no formato de `zonas` de backend/app/estetica/dimensoes.py.
"""

import argparse
import json
from pathlib import Path

ZONAS = {"1": "ilha_camera", "2": "lente_camera", "3": "recorte_tela", "4": "botao", "5": "porta"}


def para_mm(x0, y0, x1, y1, px_por_mm: float) -> list[float]:
    x, y = min(x0, x1) / px_por_mm, min(y0, y1) / px_por_mm
    return [round(x, 1), round(y, 1), round(abs(x1 - x0) / px_por_mm, 1), round(abs(y1 - y0) / px_por_mm, 1)]


def main():
    import cv2

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("imagem", type=Path)
    ap.add_argument("--face", required=True)
    ap.add_argument("--largura", type=float, required=True, help="largura da face em mm (W do referencial 7.2)")
    args = ap.parse_args()
    img = cv2.imread(str(args.imagem))
    r = img.shape[1] / args.largura
    escala = min(1.0, 1400 / img.shape[0])
    zona, inicio, rets = "ilha_camera", None, []

    def mouse(ev, x, y, *_):
        nonlocal inicio
        if ev == cv2.EVENT_LBUTTONDOWN:
            inicio = (x / escala, y / escala)
        elif ev == cv2.EVENT_LBUTTONUP and inicio:
            rets.append((zona, para_mm(*inicio, x / escala, y / escala, r)))
            inicio = None

    cv2.namedWindow("zonas")
    cv2.setMouseCallback("zonas", mouse)
    while True:
        tela = img.copy()
        for z, (x, y, w, h) in rets:
            cv2.rectangle(tela, (int(x * r), int(y * r)), (int((x + w) * r), int((y + h) * r)), (0, 200, 255), 2)
            cv2.putText(tela, z, (int(x * r), int(y * r) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        cv2.putText(tela, f"zona: {zona}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("zonas", cv2.resize(tela, None, fx=escala, fy=escala))
        k = chr(cv2.waitKey(30) & 0xFF)
        if k in ZONAS:
            zona = ZONAS[k]
        elif k == "u" and rets:
            rets.pop()
        elif k == "s":
            saida = {args.face: {}}
            for z, ret in rets:
                saida[args.face].setdefault(z, []).append(ret)
            destino = args.imagem.with_suffix(".zonas.json")
            destino.write_text(json.dumps(saida, indent=2))
            print(destino)
        elif k == "q":
            break


if __name__ == "__main__":
    main()
