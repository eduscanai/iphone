"""Gera o dataset COCO do detector a partir das avaliações (guia 12.4).

- Positivos: defeitos confirmados e desenhados pelo técnico (avaliação vigente, humana).
- Negativos difíceis: propostas rejeitadas viram blocos sem anotação.
- Imagens: faces retificadas (luz ambiente) cortadas em blocos de 640 px com 20% de sobreposição.
- Divisão por APARELHO, nunca por foto: usa `sessao_estetica.conjunto` (hash do IMEI, o mesmo do
  backend). O conjunto `teste` é o holdout do gate e nunca entra no treino.

    uv run --extra dados python -I ferramentas/exportar_dataset.py --saida dados/coco/defeitos-v1

Variáveis: DATABASE_URL (postgresql://…) e o storage (ESTETICA_ARMAZENAMENTO, ESTETICA_DIR_FOTOS
ou S3_*), as mesmas do backend.
"""

import argparse
import io
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visao.blocos import Bloco, blocos  # noqa: E402

CLASSES = ["risco", "trinca", "lascado", "amassado", "descascado", "desgaste", "mancha"]
PASTAS = {"treino": "train", "validacao": "valid", "teste": "test"}
LADO, SOBREPOSICAO = 640, 0.2

SQL = """
WITH vigente AS (
  SELECT a.* FROM avaliacao_estetica a
   WHERE a.origem <> 'automatica'
     AND NOT EXISTS (SELECT 1 FROM avaliacao_estetica b WHERE b.substitui_id = a.id)
)
SELECT v.sessao_id::text, se.conjunto, d.face, d.tipo, d.estado, d.caixa_mm, d.origem
  FROM vigente v
  JOIN sessao_estetica se ON se.sessao_id = v.sessao_id
  JOIN defeito_estetico d ON d.avaliacao_id = v.id
"""

SQL_FOTOS = """
SELECT f.sessao_id::text, f.chave_retificada, f.geometria
  FROM foto_estetica f
 WHERE f.luz = 'ambiente' AND f.aceita AND f.chave_retificada IS NOT NULL AND f.sessao_id::text = ANY(%s)
 ORDER BY f.criada_em
"""


def anotacoes_do_bloco(b: Bloco, defeitos: list[dict], r: float, min_visivel=0.5) -> list[dict]:
    """Defeitos (caixa em mm) que caem no bloco, recortados; descarta os que ficam < 50% dentro."""
    out = []
    for d in defeitos:
        x, y, w, h = (v * r for v in d["caixa_mm"])
        x0, y0 = max(x, b.x), max(y, b.y)
        x1, y1 = min(x + max(w, 2), b.x + b.w), min(y + max(h, 2), b.y + b.h)
        if x1 <= x0 or y1 <= y0:
            continue
        if (x1 - x0) * (y1 - y0) < min_visivel * max(w, 2) * max(h, 2):
            continue
        out.append({"bbox": [round(x0 - b.x, 1), round(y0 - b.y, 1), round(x1 - x0, 1), round(y1 - y0, 1)],
                    "category_id": CLASSES.index(d["tipo"])})
    return out


def montar(sessoes: dict, imagens: dict, r_por_imagem: dict, saida: Path) -> dict:
    """sessoes: sessao → {conjunto, face → {positivos, rejeitados}}; imagens: (sessao, face) → np.ndarray."""
    cocos = {c: {"images": [], "annotations": [], "categories": [{"id": i, "name": n, "supercategory": "defeito"}
                                                                  for i, n in enumerate(CLASSES)]} for c in PASTAS}
    contagem = defaultdict(int)
    for (sessao, face), img in imagens.items():
        info = sessoes[sessao]
        conjunto = info["conjunto"]
        r = r_por_imagem[(sessao, face)]
        pos = info["faces"].get(face, {}).get("positivos", [])
        rej = info["faces"].get(face, {}).get("rejeitados", [])
        pasta = saida / PASTAS[conjunto]
        pasta.mkdir(parents=True, exist_ok=True)
        for b in blocos(*img.shape[:2], LADO, SOBREPOSICAO):
            anots = anotacoes_do_bloco(b, pos, r)
            negativo = not anots and anotacoes_do_bloco(b, rej, r)
            if not anots and not negativo:
                continue  # bloco liso sem nada: não ajuda o treino
            nome = f"{sessao[:8]}_{face}_{b.x}_{b.y}.jpg"
            Image.fromarray(img[b.y:b.y + b.h, b.x:b.x + b.w]).save(pasta / nome, quality=92)
            coco = cocos[conjunto]
            img_id = len(coco["images"])
            coco["images"].append({"id": img_id, "file_name": nome, "width": b.w, "height": b.h})
            for a in anots:
                coco["annotations"].append(a | {"id": len(coco["annotations"]), "image_id": img_id,
                                                "area": a["bbox"][2] * a["bbox"][3], "iscrowd": 0})
            contagem[(conjunto, "negativos" if negativo else "positivos")] += 1
    for c, coco in cocos.items():
        (saida / PASTAS[c]).mkdir(parents=True, exist_ok=True)
        (saida / PASTAS[c] / "_annotations.coco.json").write_text(json.dumps(coco))
    return dict(contagem)


def _ler_storage(chave: str) -> bytes:
    if os.environ.get("ESTETICA_ARMAZENAMENTO", "disco") == "s3":
        import boto3

        s3 = boto3.client("s3", endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
                          aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID"),
                          aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"))
        return s3.get_object(Bucket=os.environ.get("S3_BUCKET_ESTETICA", "morecheck-estetica"), Key=chave)["Body"].read()
    raiz = Path(os.environ.get("ESTETICA_DIR_FOTOS", Path.home() / ".morecheck" / "fotos-dev"))
    return (raiz / chave).read_bytes()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, required=True)
    args = ap.parse_args()
    import psycopg

    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    sessoes: dict = defaultdict(lambda: {"conjunto": None, "faces": defaultdict(lambda: {"positivos": [], "rejeitados": []})})
    with psycopg.connect(url) as c:
        for sid, conjunto, face, tipo, estado, caixa, _origem in c.execute(SQL):
            s = sessoes[sid]
            s["conjunto"] = conjunto
            if tipo not in CLASSES:
                continue  # anomalia sem classe não treina o detector
            s["faces"][face]["rejeitados" if estado == "rejeitado" else "positivos"].append({"tipo": tipo, "caixa_mm": caixa})
        imagens, rs = {}, {}
        for sid, chave, geometria in c.execute(SQL_FOTOS, (list(sessoes),)):
            for g in geometria or []:
                face = g["face"]
                if (sid, face) in imagens or face not in sessoes[sid]["faces"]:
                    continue
                img = np.array(Image.open(io.BytesIO(_ler_storage(f"{chave}_{face}.jpg"))).convert("RGB"))
                imagens[(sid, face)] = img
                rs[(sid, face)] = 1 / g["mm_por_px"] if g.get("mm_por_px") else 20.0
    print(montar(sessoes, imagens, rs, args.saida))


if __name__ == "__main__":
    main()
