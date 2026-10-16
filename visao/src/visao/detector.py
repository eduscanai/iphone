"""Camada (c): detector de defeitos RF-DETR (Apache-2.0; guia R15 e 15.7) em blocos da face
retificada. Ultralytics fica de fora (AGPL-3.0; D7)."""

import numpy as np

from . import blocos as bl
from . import zonas
from .modelos import CLASSES_DETECTOR, Modelos

LADO_BLOCO = 640
SOBREPOSICAO = 0.2


def detectar(modelos: Modelos, face: str, ret: np.ndarray, rot: np.ndarray, r: float) -> list[dict]:
    if modelos.detector is None:
        return []
    from PIL import Image

    rgb = np.repeat((np.clip(ret, 0, 1) * 255).astype(np.uint8)[..., None], 3, axis=2)
    achados = []
    limiar_min = min(modelos.limiares.values())
    for b in bl.blocos(*ret.shape, LADO_BLOCO, SOBREPOSICAO):
        img = Image.fromarray(rgb[b.y:b.y + b.h, b.x:b.x + b.w])
        det = modelos.detector.predict(img, threshold=limiar_min)  # VERIFICAR a assinatura na versão instalada
        for caixa, classe, conf in zip(det.xyxy, det.class_id, det.confidence, strict=True):
            tipo = CLASSES_DETECTOR[int(classe)] if int(classe) < len(CLASSES_DETECTOR) else None
            if tipo is None or conf < modelos.limiares.get(tipo, modelos.limiares["padrao"]):
                continue
            caixa_mm = bl.caixa_bloco_para_mm(caixa, b, r)
            x, y, w, h = caixa_mm
            centro = np.array([[(x + w / 2) * r, (y + h / 2) * r]])
            achados.append({"face": face, "fonte": "detector", "tipo": tipo, "zona": zonas.zona_de(rot, centro),
                            "caixa_mm": caixa_mm, "maior_dimensao_mm": round(max(w, h), 2),
                            "comprimento_mm": round(float(np.hypot(w, h)), 2) if tipo in ("risco", "trinca") else None,
                            "area_mm2": round(w * h, 2), "confianca": round(float(conf), 3), "visibilidade": "visivel"})
    return bl.nms_mm(achados)
