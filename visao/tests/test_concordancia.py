import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "ferramentas"))
import concordancia as cc  # noqa: E402


def test_metricas_perfeitas():
    m = cc.metricas(list("AABBCCDD"), list("AABBCCDD"))
    assert m["exata"] == 1 and m["a_2_ou_mais"] == 0 and m["kappa_quadratico"] == pytest.approx(1)


def test_metricas_com_erro_de_2_notas():
    m = cc.metricas(list("AABBCCDD"), list("AABBCCDB"))
    assert m["exata"] == pytest.approx(7 / 8)
    assert m["a_2_ou_mais"] == 1
    assert m["kappa_quadratico"] < 1


def test_recall_por_nota():
    r = cc.recall_por_nota(list("AABB"), list("ABBB"))
    assert r == {"A": 0.5, "B": 1.0, "C": None, "D": None}


def test_cli(tmp_path):
    cab = "aparelho_id,modelo,cor,tecnico,face,nota,observacao\n"
    (tmp_path / "a.csv").write_text(cab + "A1,iPhone 13,,ana,frente,B,\nA1,iPhone 13,,ana,traseira,A,\nA2,,,ana,final,C,\n")
    (tmp_path / "b.csv").write_text(cab + "A1,iPhone 13,,bia,frente,B,\nA1,iPhone 13,,bia,traseira,A,\nA2,,,bia,final,A,risco?\n")
    saida = subprocess.run(
        [sys.executable, "-I", "ferramentas/concordancia.py", str(tmp_path / "a.csv"), str(tmp_path / "b.csv")],
        capture_output=True, text=True, cwd=Path(__file__).parents[1], check=True,
    ).stdout
    assert "NOTA FINAL: 2 aparelhos" in saida
    assert "A2 final: C × A" in saida
