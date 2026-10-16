import time

from tests.conftest import Loja_


def test_tela_preta_chega_no_aparelho(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    assert cliente.post(f"/cabine/{s.token}/tela", headers=l.h_cabine, json={"acao": "preto"}).status_code == 202
    r = cliente.get(f"/pagina/{s.token}/eventos?apos=0").json()
    assert r["eventos"] == [{"seq": r["eventos"][0]["seq"], "tipo": "tela", "dados": {"acao": "preto"}}]
    seq = r["eventos"][0]["seq"]
    t0 = time.monotonic()
    assert cliente.get(f"/pagina/{s.token}/eventos?apos={seq}").json() == {"eventos": []}
    assert time.monotonic() - t0 >= 0.9  # esperou o tempo-limite (1 s nos testes)


def test_acao_invalida_e_token_errado(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    assert cliente.post(f"/cabine/{s.token}/tela", headers=l.h_cabine, json={"acao": "piscar"}).status_code == 422
    assert cliente.get("/pagina/nao-existe/eventos").status_code == 404
