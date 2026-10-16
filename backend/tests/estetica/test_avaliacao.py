from sqlalchemy import select

from app.estetica.modelos import DefeitoEstetico, SessaoEstetica, SugestaoEstetica
from tests.conftest import Loja_, defeito, fluxo_ate_sugestao

FACES_A = {f: "A" for f in ("frente", "traseira", "lat_esq", "lat_dir", "topo", "base")}


def _detalhe(cliente, l, s):
    return cliente.get(f"/estetica/sessoes/{s.id}", headers=l.h_tecnico).json()


def test_sugestao_gerada_pelo_criterio(cliente, db):
    l = Loja_(cliente, db)
    s, _ = fluxo_ate_sugestao(cliente, l, [defeito(comp=9.8), defeito(comp=2), defeito(comp=4)])
    sug = db.scalar(select(SugestaoEstetica).where(SugestaoEstetica.sessao_id == s.id))
    assert sug.nota_final == "B"
    assert sug.justificativas["frente"] == ["Tela: De 3 a 5 riscos só rasante — 3 riscos só rasante (maior 9,8 mm) → B"]
    assert db.get(SessaoEstetica, s.id).status == "aguardando_tecnico"
    r = cliente.get(f"/cabine/{s.token}/sugestao", headers=l.h_cabine).json()
    assert r["status"] == "pronta" and r["mostrar"] and r["nota_final"] == "B"
    assert r["resumo"] == sug.justificativas["frente"]
    fila = cliente.get("/estetica/fila", headers=l.h_tecnico).json()
    assert [f["sessao_id"] for f in fila] == [str(s.id)]


def test_confirmar_tudo_vira_sugerida(cliente, db):
    l = Loja_(cliente, db)
    s, reg = fluxo_ate_sugestao(cliente, l, [defeito(comp=6)])
    d = _detalhe(cliente, l, s)
    corpo = {"sessao_id": str(s.id), "notas_por_face": d["sugestao"]["notas_por_face"], "nota_final": "B",
             "defeitos": [{"proposta_id": d["defeitos_propostos"][0]["id"], "estado": "confirmado"}]}
    r = cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico, json=corpo)
    assert r.status_code == 201, r.text
    assert r.json()["origem"] == "sugerida" and r.json()["nota_regra"] == "B"
    assert db.get(SessaoEstetica, s.id).status == "avaliada"
    copias = db.scalars(select(DefeitoEstetico).where(DefeitoEstetico.avaliacao_id.is_not(None))).all()
    assert len(copias) == 1 and copias[0].estado == "confirmado" and copias[0].proposta_id is not None
    propostas = db.scalars(select(DefeitoEstetico).where(DefeitoEstetico.sugestao_id.is_not(None))).all()
    assert propostas[0].estado == "proposto"  # a proposta original nunca muda
    assert cliente.get(f"/cabine/{s.token}", headers=l.h_cabine).status_code == 409  # já avaliada


def test_rejeitar_proposta_recalcula_regra(cliente, db):
    l = Loja_(cliente, db)
    s, reg = fluxo_ate_sugestao(cliente, l, [defeito(comp=6)])
    pid = _detalhe(cliente, l, s)["defeitos_propostos"][0]["id"]
    base = {"sessao_id": str(s.id), "notas_por_face": FACES_A,
            "defeitos": [{"proposta_id": pid, "estado": "rejeitado"}]}
    r = cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico, json=base | {"nota_final": "A"})
    assert r.status_code == 201 and r.json()["nota_regra"] == "A" and r.json()["origem"] == "tecnico"


def test_nota_diferente_da_regra_exige_justificativa(cliente, db):
    l = Loja_(cliente, db)
    s, reg = fluxo_ate_sugestao(cliente, l, [defeito(comp=6)])
    d = _detalhe(cliente, l, s)
    corpo = {"sessao_id": str(s.id), "notas_por_face": d["sugestao"]["notas_por_face"] | {"frente": "C"},
             "nota_final": "C"}
    r = cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico, json=corpo)
    assert r.status_code == 422 and "Justificativa obrigatória" in r.text
    r = cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico,
                     json=corpo | {"justificativa": "Risco atravessa a câmera frontal"})
    assert r.status_code == 201 and r.json()["origem"] == "tecnico"


def test_defeito_novo_e_correcao(cliente, db):
    l = Loja_(cliente, db)
    s, reg = fluxo_ate_sugestao(cliente, l, [])
    novo = {"novo": {"face": "lat_dir", "tipo": "amassado", "zona": "quina", "visibilidade": "visivel",
                     "caixa_mm": [1, 2, 3, 3], "maior_dimensao_mm": 4}}
    corpo = {"sessao_id": str(s.id), "notas_por_face": FACES_A | {"lat_dir": "D"}, "nota_final": "D", "defeitos": [novo]}
    r = cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico, json=corpo)
    assert r.status_code == 201 and r.json()["nota_regra"] == "D"
    primeira = r.json()["avaliacao_id"]
    r = cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico,
                     json={"sessao_id": str(s.id), "notas_por_face": FACES_A, "nota_final": "A", "substitui_id": primeira})
    assert r.status_code == 201
    avs = _detalhe(cliente, l, s)["avaliacoes"]
    assert [a["substitui_id"] for a in avs] == [None, primeira]


def test_sessao_cega_esconde_no_painel_ate_avaliar(cliente, db):
    l = Loja_(cliente, db, percentual_cego=100)
    s, reg = fluxo_ate_sugestao(cliente, l, [defeito(comp=6)])
    d = _detalhe(cliente, l, s)
    assert d["cega"] and d["sugestao"] is None and d["defeitos_propostos"] == []
    assert cliente.get(f"/cabine/{s.token}/sugestao", headers=l.h_cabine).json() == {"status": "pronta", "mostrar": False}
    # o técnico desenha o que vê; as propostas da máquina não entram na avaliação cega
    risco = {"novo": {"face": "frente", "tipo": "risco", "zona": "tela", "visibilidade": "so_rasante",
                      "caixa_mm": [1, 1, 6, 1], "comprimento_mm": 6}}
    corpo = {"sessao_id": str(s.id), "notas_por_face": FACES_A | {"frente": "B"}, "nota_final": "B", "defeitos": [risco]}
    r = cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico, json=corpo)
    assert r.status_code == 201 and r.json()["origem"] == "tecnico"  # nunca viu a sugestão
    copias = db.scalars(select(DefeitoEstetico).where(DefeitoEstetico.avaliacao_id.is_not(None))).all()
    assert [c.origem for c in copias] == ["tecnico"]
    d = _detalhe(cliente, l, s)
    assert d["sugestao"]["nota_final"] == "B"  # depois de salvar, mostra para comparação


def test_outra_loja_nao_ve(cliente, db):
    l = Loja_(cliente, db)
    s, reg = fluxo_ate_sugestao(cliente, l, [])
    outra = Loja_(cliente, db)
    assert cliente.get(f"/estetica/sessoes/{s.id}", headers=outra.h_tecnico).status_code == 404
    corpo = {"sessao_id": str(s.id), "notas_por_face": FACES_A, "nota_final": "A"}
    assert cliente.post(f"/registros/{reg.id}/estetica", headers=outra.h_tecnico, json=corpo).status_code == 404


def test_criterio_avaliar_para_o_painel(cliente, db):
    l = Loja_(cliente, db)
    r = cliente.post("/estetica/criterio/avaliar", headers=l.h_tecnico, json={"defeitos": [
        {"face": "frente", "tipo": "risco", "zona": "tela", "visibilidade": "visivel", "comprimento_mm": 2}]})
    assert r.json()["nota_final"] == "C"
