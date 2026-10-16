import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "ferramentas"))
import bases  # noqa: E402
import baixar_bases  # noqa: E402
import exportar_dataset as exp  # noqa: E402
import marcar_zonas  # noqa: E402
import treinar_patchcore  # noqa: E402

from visao import anomalia, blocos  # noqa: E402


def test_blocos_cobrem_a_imagem():
    bs = blocos.blocos(1500, 1000, 640, 0.2)
    cobertura = np.zeros((1500, 1000), bool)
    for b in bs:
        cobertura[b.y:b.y + b.h, b.x:b.x + b.w] = True
        assert b.w == 640 and b.h == 640
    assert cobertura.all()
    assert blocos.blocos(300, 200, 640, 0.2) == [blocos.Bloco(0, 0, 200, 300)]


def test_nms_por_tipo():
    d = [{"tipo": "risco", "caixa_mm": [0, 0, 10, 2], "confianca": 0.9},
         {"tipo": "risco", "caixa_mm": [0.5, 0, 10, 2], "confianca": 0.6},
         {"tipo": "trinca", "caixa_mm": [0, 0, 10, 2], "confianca": 0.5}]
    r = blocos.nms_mm(d)
    assert sorted((x["tipo"], x["confianca"]) for x in r) == [("risco", 0.9), ("trinca", 0.5)]


def test_caixa_do_bloco_para_mm():
    assert blocos.caixa_bloco_para_mm([10, 20, 50, 60], blocos.Bloco(512, 512, 640, 640), 20) == [26.1, 26.6, 2.0, 2.0]


def test_familia_por_face():
    fam = {"traseira": "vidro_fosco_escuro", "moldura": "aco"}
    assert anomalia.familia_da_face("traseira", fam) == "traseira-vidro_fosco_escuro"
    assert anomalia.familia_da_face("lat_esq", fam) == "borda-aco"
    assert anomalia.familia_da_face("frente", fam) is None


def test_classes_das_bases():
    assert bases.mapear_classe("mobile-damage-diagnosis", "Crack") == "trinca"
    assert bases.mapear_classe("mobile-damage-diagnosis", "dead pixel") is None
    with pytest.raises(KeyError):
        bases.mapear_classe("mobile-damage-diagnosis", "sujeira")
    coco = {"categories": [{"id": 0, "name": "crack"}, {"id": 1, "name": "dead pixel"}],
            "annotations": [{"id": 1, "category_id": 0}, {"id": 2, "category_id": 1}], "images": []}
    u = baixar_bases.unificar(coco, "mobile-damage-diagnosis")
    assert [a["category_id"] for a in u["annotations"]] == [bases.CLASSES_DESTINO.index("trinca")]


def test_exportacao_coco_separa_por_conjunto(tmp_path):
    img = np.zeros((1400, 720, 3), np.uint8)
    sessoes = {
        "s-treino": {"conjunto": "treino", "faces": {"frente": {"positivos": [{"tipo": "risco", "caixa_mm": [10, 10, 6, 1]}],
                                                                 "rejeitados": [{"tipo": "risco", "caixa_mm": [10, 60, 3, 1]}]}}},
        "s-teste": {"conjunto": "teste", "faces": {"frente": {"positivos": [{"tipo": "trinca", "caixa_mm": [20, 20, 10, 10]}],
                                                                "rejeitados": []}}},
    }
    c = exp.montar(sessoes, {("s-treino", "frente"): img, ("s-teste", "frente"): img},
                   {("s-treino", "frente"): 10.0, ("s-teste", "frente"): 10.0}, tmp_path)
    treino = json.loads((tmp_path / "train" / "_annotations.coco.json").read_text())
    teste = json.loads((tmp_path / "test" / "_annotations.coco.json").read_text())
    assert c[("treino", "positivos")] >= 1 and c[("treino", "negativos")] >= 1
    assert all(a["category_id"] == exp.CLASSES.index("risco") for a in treino["annotations"])
    assert all(a["category_id"] == exp.CLASSES.index("trinca") for a in teste["annotations"])
    nomes_treino = {i["file_name"] for i in treino["images"]}
    assert not any(n.startswith("s-teste") for n in nomes_treino)  # holdout nunca no treino


def test_marcar_zonas_e_limiar():
    assert marcar_zonas.para_mm(100, 200, 40, 260, 20) == [2.0, 10.0, 3.0, 3.0]
    assert treinar_patchcore.limiar_percentil(list(range(1000))) == pytest.approx(994.505, rel=1e-3)
