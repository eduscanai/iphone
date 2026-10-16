"""Treina um PatchCore por família de acabamento (guia 15.6) e calcula o limiar.

    uv run --extra treino python -I ferramentas/treinar_patchcore.py \\
        --familia traseira-vidro_fosco_escuro --dados dados/patchcore/traseira-vidro_fosco_escuro

`dados/<familia>/normal/` = blocos 256×256 de faces nota A (sem lente_camera);
`dados/<familia>/validacao/` = blocos normais separados, para o limiar (percentil 99,5).
Começar quando houver ≥ 100 faces nota A da família. VERIFICAR a API do anomalib 2.x.
"""

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]


def limiar_percentil(notas: list[float], p: float = 99.5) -> float:
    return float(np.percentile(np.asarray(notas, float), p))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--familia", required=True)
    ap.add_argument("--dados", type=Path, required=True)
    ap.add_argument("--destino", type=Path, default=Path.home() / ".morecheck" / "modelos" / "patchcore")
    args = ap.parse_args()
    from anomalib.data import Folder
    from anomalib.engine import Engine
    from anomalib.models import Patchcore

    dados = Folder(name=args.familia, root=str(args.dados), normal_dir="normal", abnormal_dir="defeito")
    modelo = Patchcore(backbone="wide_resnet50_2", layers=["layer2", "layer3"], coreset_sampling_ratio=0.1)
    motor = Engine(default_root_dir=str(RAIZ / "modelos" / "patchcore" / args.familia))
    motor.fit(model=modelo, datamodule=dados)
    previsoes = motor.predict(model=modelo, data_path=str(args.dados / "validacao"))
    notas = [float(p.pred_score) for lote in previsoes for p in (lote if isinstance(lote, list) else [lote])]
    limiar = limiar_percentil(notas)
    final = args.destino / args.familia
    final.mkdir(parents=True, exist_ok=True)
    ckpt = final / "modelo.ckpt"
    motor.trainer.save_checkpoint(str(ckpt))
    from visao.modelos import sha256

    meta = {"versao": f"pc-{date.today():%Y%m%d}", "checkpoint": "modelo.ckpt", "limiar": limiar, "sha256": sha256(ckpt),
            "n_validacao": len(notas)}
    (final / "meta.json").write_text(json.dumps(meta, indent=2))
    print(final, meta)


if __name__ == "__main__":
    main()
