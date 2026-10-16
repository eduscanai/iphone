import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.base.modelos import Auditoria, Sessao
from app.estetica import concordancia
from app.estetica.modelos import (AvaliacaoEstetica, ConfigEsteticaLoja, SessaoEstetica, SugestaoEstetica)
from tests.conftest import Loja_, defeito, fluxo_ate_sugestao

FACES = ("frente", "traseira", "lat_esq", "lat_dir", "topo", "base")


def test_kappa_quadratico():
    assert concordancia.kappa_quadratico(list("ABCD"), list("ABCD")) == pytest.approx(1)
    k = concordancia.kappa_quadratico(list("AABBCCDD"), list("AABBCCDC"))
    assert 0.9 < k < 1
    m = concordancia.metricas(list("AABBCCDD" * 5), list("AABBCCDC" * 5))
    assert m["a_2_ou_mais"] == 0 and m["recall"]["D"] == 1 and m["recall"]["C"] == pytest.approx(2 / 3)
    assert m["kappa_ic95"][0] <= m["kappa_quadratico"] <= m["kappa_ic95"][1]


def _historico(db, l, n, erro_a_cada=0, conjunto="teste", salto=1):
    """n sessões cegas avaliadas, distribuídas entre A, B, C e D."""
    for i in range(n):
        s = Sessao(id=uuid.uuid4(), loja_id=l.loja.id, token=f"h{i}-{uuid.uuid4().hex[:6]}",
                   identificador_modelo="iPhone14,5")
        db.add(s)
        db.flush()
        db.add(SessaoEstetica(sessao_id=s.id, status="avaliada", cega=True, conjunto=conjunto, roteiro_versao="roteiro-v1"))
        nota = "ABCD"[i % 4]
        maquina = "ABCD"[(i % 4 + salto) % 4] if erro_a_cada and i % erro_a_cada == 0 else nota
        sug = SugestaoEstetica(sessao_id=s.id, nota_final=maquina, notas_por_face={f: maquina for f in FACES},
                               justificativas={}, margens=[], pendencias=[], versao_visao="0.1.0",
                               versao_criterio="criterio-v1", modelos={}, tempo_ms=1)
        db.add(sug)
        db.flush()
        db.add(AvaliacaoEstetica(sessao_id=s.id, nota_final=nota, notas_por_face={f: nota for f in FACES},
                                 nota_regra=nota, origem="tecnico", cega=True, tecnico_id=l.tecnico.id,
                                 sugestao_id=sug.id, versao_criterio="criterio-v1"))
    db.commit()


def test_gate_recusa_sem_dados(cliente, db):
    l = Loja_(cliente, db)
    r = cliente.put("/estetica/config", headers=l.h_admin, json={"modo": "automatico", "percentual_cego": 10})
    assert r.status_code == 409
    assert any("aparelhos avaliados: 0" in m for m in r.json()["detail"]["motivos"])
    assert cliente.put("/estetica/config", headers=l.h_tecnico, json={"modo": "assistido", "percentual_cego": 10}).status_code == 403


def test_gate_exige_sombra_de_14_dias(cliente, db):
    l = Loja_(cliente, db, percentual_cego=100)
    _historico(db, l, 200)
    r = cliente.put("/estetica/config", headers=l.h_admin, json={"modo": "automatico", "percentual_cego": 10})
    assert r.status_code == 409 and any("sombra" in m for m in r.json()["detail"]["motivos"])
    cfg = db.get(ConfigEsteticaLoja, l.loja.id)
    cfg.sombra_iniciada_em = datetime.now(timezone.utc) - timedelta(days=15)
    db.commit()
    r = cliente.put("/estetica/config", headers=l.h_admin, json={"modo": "automatico", "percentual_cego": 10})
    assert r.status_code == 200, r.text
    rel = cliente.get("/estetica/concordancia", headers=l.h_tecnico).json()
    assert rel["geral"]["n"] == 200 and rel["geral"]["exata"] == 1 and rel["gate"]["passou"]


def test_gate_recusa_erro_de_2_notas(cliente, db):
    l = Loja_(cliente, db)
    _historico(db, l, 200, erro_a_cada=50, salto=2)  # 4 erros de 2 notas (A→C, C→A)
    cfg = db.get(ConfigEsteticaLoja, l.loja.id)
    cfg.sombra_iniciada_em = datetime.now(timezone.utc) - timedelta(days=30)
    db.commit()
    r = cliente.put("/estetica/config", headers=l.h_admin, json={"modo": "automatico", "percentual_cego": 10})
    assert r.status_code == 409


def test_gate_ignora_aparelhos_de_treino(cliente, db):
    l = Loja_(cliente, db)
    _historico(db, l, 200, conjunto="treino")
    cfg = db.get(ConfigEsteticaLoja, l.loja.id)
    cfg.sombra_iniciada_em = datetime.now(timezone.utc) - timedelta(days=30)
    db.commit()
    assert cliente.put("/estetica/config", headers=l.h_admin, json={"modo": "automatico", "percentual_cego": 10}).status_code == 409


def test_automacao_seletiva(cliente, db):
    l = Loja_(cliente, db, modo="automatico", percentual_cego=0)
    s, _ = fluxo_ate_sugestao(cliente, l, [defeito(comp=9)])  # longe dos limites → automática
    av = db.scalar(select(AvaliacaoEstetica).where(AvaliacaoEstetica.sessao_id == s.id))
    assert av.origem == "automatica" and av.nota_final == "B" and av.tecnico_id is None
    s2, _ = fluxo_ate_sugestao(cliente, l, [defeito(comp=5.2)], imei="356000000000002")  # margem 4% → técnico
    assert db.scalar(select(AvaliacaoEstetica).where(AvaliacaoEstetica.sessao_id == s2.id)) is None
    s3, _ = fluxo_ate_sugestao(cliente, l, [defeito(tipo="trinca", comp=20, vis="visivel", confianca=0.5)],
                               imei="356000000000003")  # trinca com confiança intermediária → técnico
    assert db.get(SessaoEstetica, s3.id).status == "aguardando_tecnico"
    s4, _ = fluxo_ate_sugestao(cliente, l, [defeito(tipo="anomalia", zona="vidro_traseiro", face="traseira")],
                               imei="356000000000004")
    assert db.get(SessaoEstetica, s4.id).status == "aguardando_tecnico"


def test_monitoramento_volta_para_assistido(cliente, db):
    l = Loja_(cliente, db, modo="automatico", percentual_cego=100)
    _historico(db, l, 199, erro_a_cada=3)
    s, reg = fluxo_ate_sugestao(cliente, l, [defeito(comp=9)])
    risco = {"novo": {"face": "frente", "tipo": "risco", "zona": "tela", "visibilidade": "so_rasante",
                      "caixa_mm": [1, 1, 9, 1], "comprimento_mm": 9}}
    corpo = {"sessao_id": str(s.id), "notas_por_face": {f: "A" for f in FACES} | {"frente": "B"}, "nota_final": "B",
             "defeitos": [risco]}
    assert cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico, json=corpo).status_code == 201
    db.expire_all()
    assert db.get(ConfigEsteticaLoja, l.loja.id).modo == "assistido"
    assert db.scalar(select(Auditoria).where(Auditoria.acao == "estetica.automatico_desligado")) is not None
    assert cliente.get("/estetica/config", headers=l.h_tecnico).json()["ultimo_aviso"]["motivos"]
