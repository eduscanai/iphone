"""Baixa as bases públicas permitidas em formato COCO (guia 12.3) e unifica as classes.

    uv run python -I ferramentas/baixar_bases.py mobile-damage-diagnosis --versao 1

Exige ROBOFLOW_API_KEY. Recusa bases com situação "conferir" sem --licenca-conferida e
qualquer base da lista PROIBIDAS. Registra a base em DATASETS.md.
"""

import argparse
import io
import json
import os
import sys
import zipfile
from datetime import date
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from bases import BASES, CLASSES_DESTINO, mapear_classe  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


def unificar(coco: dict, base: str) -> dict:
    """Troca as categorias pelas nossas (CLASSES_DESTINO) e descarta as classes sem destino."""
    origem = {c["id"]: c["name"] for c in coco["categories"]}
    destino_id = {nome: i for i, nome in enumerate(CLASSES_DESTINO)}
    anots = []
    for a in coco["annotations"]:
        nome = mapear_classe(base, origem[a["category_id"]])
        if nome is not None:
            anots.append(a | {"category_id": destino_id[nome]})
    return coco | {"categories": [{"id": i, "name": n, "supercategory": "defeito"} for n, i in destino_id.items()],
                   "annotations": anots}


def registrar(base: str, versao: int, n_imagens: int):
    b = BASES[base]
    mapa = ", ".join(f"{k}→{v or 'descartada'}" for k, v in b["classes"].items())
    texto = (f"\n## {b['nome']}\n- URL: {b['url']}\n- Versão: {versao} · baixada em {date.today().isoformat()}\n"
             f"- Licença: {b['licenca']} (conferida na página em {date.today().isoformat()})\n"
             f"- Atribuição: <copiar o texto pedido pela página>\n- Imagens: {n_imagens} · Classes: {mapa}\n"
             f"- Uso: pré-treino do detector\n")
    with open(RAIZ / "DATASETS.md", "a", encoding="utf-8") as f:
        f.write(texto)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", choices=sorted(BASES))
    ap.add_argument("--versao", type=int, required=True)
    ap.add_argument("--licenca-conferida", action="store_true", help="para bases com situação 'conferir'")
    args = ap.parse_args()
    b = BASES[args.base]
    if b["situacao"] != "usar" and not args.licenca_conferida:
        sys.exit(f"{b['nome']}: licença '{b['licenca']}'. Confira na página e rode com --licenca-conferida.")
    if not b["workspace"]:
        sys.exit(f"{b['nome']}: workspace/projeto do Roboflow não cadastrados em bases.py (VERIFICAR a URL).")
    chave = os.environ.get("ROBOFLOW_API_KEY")
    if not chave:
        sys.exit("Defina ROBOFLOW_API_KEY (em ~/.morecheck/producao.env; nunca no código).")
    url = f"https://api.roboflow.com/{b['workspace']}/{b['projeto']}/{args.versao}/coco"
    r = httpx.get(url, params={"api_key": chave}, timeout=60)  # VERIFICAR o formato da API do Roboflow
    r.raise_for_status()
    link = r.json()["export"]["link"]
    destino = RAIZ / "dados" / "bases" / f"{args.base}-v{args.versao}"
    with zipfile.ZipFile(io.BytesIO(httpx.get(link, timeout=600, follow_redirects=True).content)) as z:
        z.extractall(destino)
    n = 0
    for anot in destino.glob("*/_annotations.coco.json"):
        coco = unificar(json.loads(anot.read_text()), args.base)
        anot.write_text(json.dumps(coco))
        n += len(coco["images"])
    registrar(args.base, args.versao, n)
    print(f"{n} imagens em {destino}")


if __name__ == "__main__":
    main()
