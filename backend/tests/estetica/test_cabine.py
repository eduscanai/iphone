import uuid

from sqlalchemy import func, select

from app.estetica.modelos import FotoEstetica, SessaoEstetica, TarefaVisao
from tests.conftest import LUZES, Loja_, capturar_tudo, enviar_foto, jpeg


def test_pareamento_e_revogacao(cliente, db):
    l = Loja_(cliente, db)
    codigo = cliente.post("/cabines/pareamento", headers=l.h_admin).json()["codigo"]
    assert cliente.post("/cabines/ativar", json={"codigo": codigo, "nome": "C2"}).status_code == 201
    assert cliente.post("/cabines/ativar", json={"codigo": codigo, "nome": "C3"}).status_code == 400  # uso único
    assert cliente.post("/cabines/pareamento", headers=l.h_tecnico).status_code == 403  # só admin
    s, _ = l.nova_sessao()
    assert cliente.get(f"/cabine/{s.token}", headers=l.h_cabine).status_code == 200
    assert cliente.post(f"/cabines/{l.cabine_id}/revogar", headers=l.h_admin).status_code == 200
    assert cliente.get(f"/cabine/{s.token}", headers=l.h_cabine).status_code == 401


def test_abrir_sessao(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    r = cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    assert r.status_code == 200
    j = r.json()
    assert j["aparelho"]["dimensoes_mm"] == {"largura": 71.5, "altura": 146.7, "espessura": 7.65}
    assert j["roteiro"]["versao"] == "roteiro-v1"
    assert [p["luzes"] for p in j["roteiro"]["passos"]] == [LUZES, LUZES]
    assert j["mostrar_sugestao"] is True  # percentual cego 0
    se = db.get(SessaoEstetica, s.id)
    assert se.conjunto in ("treino", "validacao", "teste")


def test_erros_ao_abrir(cliente, db):
    l = Loja_(cliente, db)
    assert cliente.get("/cabine/nao-existe", headers=l.h_cabine).status_code == 404
    s, _ = l.nova_sessao(modelo="iPhone99,9")
    r = cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    assert r.status_code == 422 and "iPhone99,9 sem dimensões cadastradas" in r.text
    outra = Loja_(cliente, db, modo="desligado")
    s2, _ = outra.nova_sessao()
    assert cliente.get(f"/cabine/{s2.token}", headers=outra.h_cabine).status_code == 403
    assert cliente.get(f"/cabine/{s2.token}", headers=l.h_cabine).status_code == 404  # outra loja


def test_cega_esconde_sugestao_da_cabine(cliente, db):
    l = Loja_(cliente, db, percentual_cego=100)
    s, _ = l.nova_sessao()
    assert cliente.get(f"/cabine/{s.token}", headers=l.h_cabine).json()["mostrar_sugestao"] is False


def test_foto_idempotente(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    chave = str(uuid.uuid4())
    a = enviar_foto(cliente, l, s.token, 1, "ambiente", chave=chave)
    b = enviar_foto(cliente, l, s.token, 1, "ambiente", chave=chave)
    assert a.status_code == b.status_code == 201
    assert a.json()["foto_id"] == b.json()["foto_id"]
    assert (a.json()["duplicada"], b.json()["duplicada"]) == (False, True)
    assert db.scalar(select(func.count()).select_from(FotoEstetica)) == 1
    assert db.scalar(select(func.count()).select_from(TarefaVisao)) == 1


def test_validacao_da_foto(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    assert enviar_foto(cliente, l, s.token, 1, "contraluz").status_code == 422  # luz fora do roteiro
    assert enviar_foto(cliente, l, s.token, 1, "ambiente", face="traseira").status_code == 422
    assert enviar_foto(cliente, l, s.token, 3, "ambiente").status_code == 422  # passo inexistente
    assert enviar_foto(cliente, l, s.token, 1, "ambiente", dados=b"nao e imagem").status_code == 422
    r = cliente.post(f"/cabine/{s.token}/fotos", headers=l.h_cabine,
                     data={"passo": 1, "face": "frente", "luz": "ambiente", "pose": "deitado", "metadados": "{}"},
                     files={"arquivo": ("f.jpg", jpeg(), "image/jpeg")})
    assert r.status_code in (400, 422)  # sem Idempotency-Key / sem formato


def test_foto_grande_demais(cliente, db, monkeypatch):
    from app.config import config

    monkeypatch.setattr(config(), "estetica_tamanho_max_mb", 0)
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    assert enviar_foto(cliente, l, s.token, 1, "ambiente").status_code == 413


def test_concluir_exige_roteiro_completo(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    enviar_foto(cliente, l, s.token, 1, "ambiente")
    r = cliente.post(f"/cabine/{s.token}/concluir", headers=l.h_cabine, json={"fotos_enviadas": 1})
    assert r.status_code == 409
    faltando = r.json()["detail"]["faltando"]
    assert {"passo": 2, "luz": "ambiente"} in faltando and len(faltando) == 5


def test_concluir_cria_fusao_uma_vez(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    capturar_tudo(cliente, l, s.token)
    cliente.post(f"/cabine/{s.token}/concluir", headers=l.h_cabine, json={"fotos_enviadas": 6})
    n = db.scalar(select(func.count()).select_from(TarefaVisao).where(TarefaVisao.tipo == "fusao"))
    assert n == 1
    assert cliente.get(f"/cabine/{s.token}/sugestao", headers=l.h_cabine).json()["status"] == "processando"


def test_perfil_calibracao(cliente, db):
    l = Loja_(cliente, db)
    assert cliente.put("/cabine/perfil", headers=l.h_cabine, json={"versao": 3, "foco": {"deitado": 0.62}}).status_code == 200
    assert cliente.put("/cabine/perfil", headers=l.h_cabine, json={"foco": {}}).status_code == 422
    assert cliente.get("/cabines", headers=l.h_admin).json()[0]["perfil_versao"] == 3
