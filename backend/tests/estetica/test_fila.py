import threading
from datetime import datetime, timedelta, timezone

from app.estetica import fila
from app.estetica.modelos import SessaoEstetica, TarefaVisao
from app.db import nova_sessao
from tests.conftest import WORKER, Loja_, capturar_tudo, enviar_foto, fundir, processar_fotos


def _reservar(cliente, tipos=("foto", "fusao"), worker="w1", token=WORKER):
    return cliente.post("/visao/tarefas/reservar", headers=token, json={"worker_id": worker, "tipos": list(tipos)})


def test_worker_sem_token(cliente):
    assert cliente.post("/visao/tarefas/reservar", json={"worker_id": "x"}).status_code == 401
    assert _reservar(cliente, token={"Authorization": "Bearer errado"}).status_code == 401


def test_rasante_espera_ambiente(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    enviar_foto(cliente, l, s.token, 1, "rasante_a")
    assert _reservar(cliente).status_code == 204
    enviar_foto(cliente, l, s.token, 1, "ambiente")
    luzes = {_reservar(cliente).json()["foto"]["luz"] for _ in range(2)}
    assert luzes == {"rasante_a", "ambiente"}


def test_tarefa_foto_traz_irmas_e_uploads_por_face(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    enviar_foto(cliente, l, s.token, 1, "ambiente")
    enviar_foto(cliente, l, s.token, 1, "rasante_a")
    t = _reservar(cliente).json()
    t2 = _reservar(cliente).json()
    ras = t if t["foto"]["luz"] == "rasante_a" else t2
    assert [i["luz"] for i in ras["fotos_irmas"]] == ["ambiente"]
    assert set(ras["upload"]["retificada"]) == {"frente", "lat_esq", "lat_dir", "topo", "base"}
    assert ras["aparelho"]["familia"] == {"traseira": "vidro_brilhante_escuro", "moldura": "aluminio_escuro"}


def test_fusao_so_depois_das_fotos(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    capturar_tudo(cliente, l, s.token)
    assert _reservar(cliente, tipos=["fusao"]).status_code == 204
    assert processar_fotos(cliente) == 6
    t = _reservar(cliente, tipos=["fusao"]).json()
    assert t["tipo"] == "fusao" and len(t["fotos"]) == 6
    assert all(f["resultado"]["qualidade"]["ok"] for f in t["fotos"])


def test_lease_vencido_e_tentativas(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    enviar_foto(cliente, l, s.token, 1, "ambiente")
    for tentativa in range(1, 4):
        t = _reservar(cliente).json()
        with nova_sessao() as d:
            tv = d.get(TarefaVisao, t["tarefa_id"])
            assert tv.tentativas == tentativa
            tv.reservada_ate = datetime.now(timezone.utc) - timedelta(seconds=1)
            d.commit()
    assert _reservar(cliente).status_code == 204
    with nova_sessao() as d:
        assert d.get(TarefaVisao, t["tarefa_id"]).status == "falhou"


def test_renovar_e_falha_recuperavel(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    enviar_foto(cliente, l, s.token, 1, "ambiente")
    t = _reservar(cliente).json()
    assert cliente.post(f"/visao/tarefas/{t['tarefa_id']}/renovar", headers=WORKER, json={"worker_id": "w1"}).status_code == 200
    assert cliente.post(f"/visao/tarefas/{t['tarefa_id']}/renovar", headers=WORKER, json={"worker_id": "w2"}).status_code == 409
    r = cliente.post(f"/visao/tarefas/{t['tarefa_id']}/falha", headers=WORKER, json={"erro": "timeout", "recuperavel": True})
    assert r.json()["status"] == "pendente"
    t = _reservar(cliente).json()
    r = cliente.post(f"/visao/tarefas/{t['tarefa_id']}/falha", headers=WORKER, json={"erro": "bug", "recuperavel": False})
    assert r.json()["status"] == "falhou"
    eventos = cliente.get(f"/cabine/{s.token}/eventos?apos=0", headers=l.h_cabine).json()["eventos"]
    assert eventos[0]["tipo"] == "foto_reprovada"


def test_reservas_concorrentes_nao_repetem(cliente, db):
    l = Loja_(cliente, db)
    for _ in range(4):
        s, _ = l.nova_sessao()
        cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
        for luz in ("ambiente",):
            enviar_foto(cliente, l, s.token, 1, luz)
            enviar_foto(cliente, l, s.token, 2, luz)
    pegas, trava = [], threading.Lock()

    def worker(nome):
        with nova_sessao() as d:
            while (t := fila.reservar(d, nome, ["foto"])) is not None:
                with trava:
                    pegas.append(t.id)

    ths = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(4)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    assert len(pegas) == 8 and len(set(pegas)) == 8


def test_foto_reprovada_vira_refazer(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    capturar_tudo(cliente, l, s.token)
    processar_fotos(cliente, ok=False)
    r = cliente.get(f"/cabine/{s.token}/sugestao", headers=l.h_cabine).json()
    assert set(r["refazer"]) == {"frente", "traseira"}


def test_foto_nova_depois_de_concluir_invalida_fusao(cliente, db):
    l = Loja_(cliente, db)
    s, _ = l.nova_sessao()
    cliente.get(f"/cabine/{s.token}", headers=l.h_cabine)
    capturar_tudo(cliente, l, s.token)
    processar_fotos(cliente)
    enviar_foto(cliente, l, s.token, 1, "ambiente")  # refazendo a frente
    assert db.get(SessaoEstetica, s.id).status == "capturando"
    assert _reservar(cliente, tipos=["fusao"]).status_code == 204  # a fusão antiga foi cancelada
    processar_fotos(cliente)
    cliente.post(f"/cabine/{s.token}/concluir", headers=l.h_cabine, json={"fotos_enviadas": 7})
    fundir(cliente)
    db.expire_all()
    assert db.get(SessaoEstetica, s.id).status == "aguardando_tecnico"
