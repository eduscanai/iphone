"""Treina o RF-DETR (guia 15.7) e registra o modelo em MODELOS.md.

    uv run --extra treino python -I ferramentas/treinar_detector.py \\
        --dataset dados/coco/defeitos-v1 --versao rfdetr-s-defeitos-v1 [--base modelos/rfdetr-s-base-v1/pesos.pth]

Pré-treino com bases públicas (12.3), depois ajuste fino com as marcações do painel (12.4).
VERIFICAR nomes e parâmetros na versão instalada do rfdetr. Não usar XL/2XL nem rfdetr_plus (18.1).
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visao.modelos import CLASSES_DETECTOR, LIMIARES_PADRAO, sha256  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, required=True)
    ap.add_argument("--versao", required=True)
    ap.add_argument("--base", type=Path, help="pesos do pré-treino (ajuste fino)")
    ap.add_argument("--epocas", type=int, default=60)
    ap.add_argument("--lote", type=int, default=4)
    ap.add_argument("--acumular", type=int, default=4, help="grad_accum_steps (lote efetivo = lote × acumular)")
    ap.add_argument("--dispositivo", default=None, help="cpu, mps ou cuda (padrão: VISAO_DISPOSITIVO ou automático)")
    ap.add_argument("--resolucao", type=int, default=None, help="múltiplo de 32 (padrão do modelo: 512)")
    ap.add_argument("--sem-registro", action="store_true", help="não anota em MODELOS.md (testes)")
    ap.add_argument("--processos", type=int, default=None,
                    help="processos de carga de dados (padrão: 0 fora de CUDA; no macOS, vários processos travam)")
    ap.add_argument("--destino", type=Path, default=Path.home() / ".morecheck" / "modelos" / "detector")
    args = ap.parse_args()
    import os

    from rfdetr import RFDETRSmall

    saida = RAIZ / "modelos" / args.versao
    dispositivo = args.dispositivo or os.environ.get("VISAO_DISPOSITIVO")
    extra = {"device": dispositivo} if dispositivo else {}
    if args.base:
        extra |= {"pretrain_weights": str(args.base), "trust_checkpoint": True}
    modelo = RFDETRSmall(**extra)
    modelo.train(dataset_dir=str(args.dataset), epochs=args.epocas, batch_size=args.lote, grad_accum_steps=args.acumular,
                 lr=1e-4, output_dir=str(saida), seed=42,
                 **({"resolution": args.resolucao} if args.resolucao else {}),
                 # aumento de dados por GPU (kornia) só existe em CUDA. No Mac, "cpu" é resolvido para
                 # kornia e depois recusado (rfdetr 1.11): pedir torchvision direto.
                 augmentation_backend="auto" if (dispositivo or "").startswith("cuda") else "torchvision",
                 num_workers=args.processos if args.processos is not None else (2 if (dispositivo or "").startswith("cuda") else 0),
                 **({"device": dispositivo} if dispositivo else {}))
    candidatos = sorted(saida.glob("checkpoint_best*.pth")) or sorted(saida.glob("*.pth"))
    if not candidatos:
        sys.exit(f"Nenhum checkpoint em {saida}")
    pesos = candidatos[0]
    print("checkpoint escolhido:", pesos.name)
    final = args.destino / args.versao
    final.mkdir(parents=True, exist_ok=True)
    shutil.copy(pesos, final / "pesos.pth")
    hash_ = sha256(final / "pesos.pth")
    meta = {"versao": args.versao, "pesos": "pesos.pth", "sha256": hash_, "classes": CLASSES_DETECTOR,
            "limiares": LIMIARES_PADRAO, "dataset": str(args.dataset), "base": str(args.base) if args.base else None}
    (final / "meta.json").write_text(json.dumps(meta, indent=2))
    if args.sem_registro:
        print(final)
        return
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "—"
    with open(RAIZ / "MODELOS.md", "a", encoding="utf-8") as f:
        f.write(f"\n## {args.versao}\n- SHA-256: `{hash_}`\n- Código: commit {commit}\n- Dados: {args.dataset}"
                f"{' · base ' + str(args.base) if args.base else ''}\n- Treino: RF-DETR S, {args.epocas} épocas, lr 1e-4, "
                f"lote 4×4, semente 42\n- Métricas (holdout próprio): <preencher com a avaliação no conjunto teste>\n"
                f"- Data: {date.today().isoformat()} · Guardado em: {final}\n")
    print(final)


if __name__ == "__main__":
    main()
