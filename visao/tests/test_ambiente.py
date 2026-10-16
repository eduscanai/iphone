import os

from visao import ambiente


def test_le_arquivo_sem_sobrescrever(tmp_path, monkeypatch):
    prod, dev = tmp_path / "producao.env", tmp_path / "desenvolvimento.env"
    prod.write_text("A=prod\n")
    dev.write_text("# comentário\nA=dev\nB='dev b'\nC=shell?\n")
    monkeypatch.setenv("C", "do shell")
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    assert ambiente.carregar((prod, dev, tmp_path / "nao-existe.env")) == [prod, dev]
    assert (os.environ["A"], os.environ["B"], os.environ["C"]) == ("prod", "dev b", "do shell")
