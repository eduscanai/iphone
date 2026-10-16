"""Modelos treinados (camadas b e c), carregados uma vez por worker (guia 12.2).

Pasta (VISAO_DIR_MODELOS, padrão ~/.morecheck/modelos):
    detector/<versao>/pesos.pth + meta.json   (RF-DETR; meta: classes, sha256, limiares)
    patchcore/<familia>/modelo.ckpt + meta.json  (meta: limiar, sha256)

Sem pasta ou sem as dependências de treino, o worker segue só com a camada (a).
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("visao.modelos")

CLASSES_DETECTOR = ["risco", "trinca", "lascado", "amassado", "descascado", "desgaste", "mancha"]
# Trinca é o erro mais caro (nota D): limiar mais baixo, privilegia recall (guia 15.7)
LIMIARES_PADRAO = {"trinca": 0.25, "padrao": 0.45}


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


@dataclass
class Modelos:
    detector: object | None = None
    versao_detector: str | None = None
    limiares: dict = field(default_factory=lambda: dict(LIMIARES_PADRAO))
    patchcore: dict[str, tuple[object, float]] = field(default_factory=dict)  # família → (modelo, limiar)
    versoes_patchcore: dict[str, str] = field(default_factory=dict)

    @property
    def descricao(self) -> dict:
        d = {}
        if self.versao_detector:
            d["detector"] = self.versao_detector
        if self.versoes_patchcore:
            d["patchcore"] = dict(self.versoes_patchcore)
        return d


def carregar(pasta: str | Path | None = None, dispositivo: str | None = None) -> Modelos:
    pasta = Path(pasta or os.environ.get("VISAO_DIR_MODELOS", Path.home() / ".morecheck" / "modelos")).expanduser()
    dispositivo = dispositivo or os.environ.get("VISAO_DISPOSITIVO", "cpu")
    m = Modelos()
    det = sorted((pasta / "detector").glob("*/meta.json")) if (pasta / "detector").exists() else []
    if det:
        meta_p = det[-1]
        meta = json.loads(meta_p.read_text())
        pesos = meta_p.parent / meta.get("pesos", "pesos.pth")
        if meta.get("sha256") and sha256(pesos) != meta["sha256"]:
            raise RuntimeError(f"Hash dos pesos do detector não confere: {pesos}")
        try:
            from rfdetr import RFDETRSmall  # VERIFICAR o nome da classe na versão instalada

            m.detector = RFDETRSmall(pretrain_weights=str(pesos), device=dispositivo)
            m.versao_detector = f"{meta_p.parent.name}+{meta.get('sha256', '')[:7]}"
            m.limiares.update(meta.get("limiares", {}))
        except ImportError:
            log.warning("rfdetr não instalado (uv sync --extra treino): detector desligado")
    for meta_p in sorted((pasta / "patchcore").glob("*/meta.json")) if (pasta / "patchcore").exists() else []:
        meta = json.loads(meta_p.read_text())
        try:
            from anomalib.models import Patchcore  # VERIFICAR a API do anomalib 2.x

            modelo = Patchcore.load_from_checkpoint(str(meta_p.parent / meta.get("checkpoint", "modelo.ckpt")))
            modelo.eval()
            m.patchcore[meta_p.parent.name] = (modelo, float(meta["limiar"]))
            m.versoes_patchcore[meta_p.parent.name] = f"{meta.get('versao', 'pc')}+{meta.get('sha256', '')[:7]}"
        except ImportError:
            log.warning("anomalib não instalado: PatchCore desligado")
            break
    return m
