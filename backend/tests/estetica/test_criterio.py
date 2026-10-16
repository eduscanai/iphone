import copy

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.estetica import criterio as cr
from app.estetica.criterio import DefeitoEntrada as D
from app.estetica.enums import EstadoDefeito, Face, Nota, TipoDefeito, Visibilidade, Zona

V, R = Visibilidade.visivel, Visibilidade.so_rasante


def risco(comp, face=Face.frente, zona=Zona.tela, vis=R, **kw):
    return D(face=face, tipo=TipoDefeito.risco, zona=zona, visibilidade=vis, comprimento_mm=comp, **kw)


def notas(defeitos):
    return cr.avaliar(defeitos)


# ---------------------------------------------------------------- exemplos resolvidos
# Cada exemplo de docs/nota-estetica-criterio.md tem um caso aqui (mesmo número).

EXEMPLOS = [
    # (n, descrição, defeitos, nota da face frente, nota final)
    (1, "aparelho sem defeitos", [], Nota.A, Nota.A),
    (2, "2 riscos só rasante de 3 mm na tela", [risco(3), risco(3)], Nota.A, Nota.A),
    (3, "3 riscos só rasante, maior 9,8 mm", [risco(2), risco(4), risco(9.8)], Nota.B, Nota.B),
    (4, "1 risco só rasante de 6 mm", [risco(6)], Nota.B, Nota.B),
    (5, "1 risco visível de 2 mm", [risco(2, vis=V)], Nota.C, Nota.C),
    (6, "1 risco só rasante de 16 mm", [risco(16)], Nota.C, Nota.C),
    (7, "6 riscos só rasante de 1 mm", [risco(1)] * 6, Nota.C, Nota.C),
    (8, "trinca na tela", [D(face=Face.frente, tipo=TipoDefeito.trinca, zona=Zona.tela, visibilidade=V, comprimento_mm=30)],
     Nota.D, Nota.D),
    (9, "amassado de 2 mm na quina", [D(face=Face.lat_dir, tipo=TipoDefeito.amassado, zona=Zona.quina, visibilidade=V,
                                         maior_dimensao_mm=2)], Nota.A, Nota.C),
    (10, "amassado de 4 mm na moldura", [D(face=Face.topo, tipo=TipoDefeito.amassado, zona=Zona.moldura, visibilidade=V,
                                            maior_dimensao_mm=4)], Nota.A, Nota.D),
    (11, "2 marcas de 0,8 mm na moldura", [risco(0.8, face=Face.lat_esq, zona=Zona.moldura)] * 2, Nota.A, Nota.A),
    (12, "marca de 2 mm na moldura", [risco(2, face=Face.lat_esq, zona=Zona.moldura)], Nota.A, Nota.B),
    (13, "risco só rasante na lente da câmera", [risco(1, face=Face.traseira, zona=Zona.lente_camera)], Nota.A, Nota.C),
    (14, "risco de 6 mm na tela e trinca na traseira",
     [risco(6), D(face=Face.traseira, tipo=TipoDefeito.trinca, zona=Zona.vidro_traseiro, visibilidade=V)], Nota.B, Nota.D),
]


@pytest.mark.parametrize("n,descricao,defeitos,nota_frente,nota_final", EXEMPLOS, ids=[f"ex{e[0]}" for e in EXEMPLOS])
def test_exemplos(n, descricao, defeitos, nota_frente, nota_final):
    r = notas(defeitos)
    assert r.notas_por_face[Face.frente] == nota_frente
    assert r.nota_final == nota_final


def test_justificativa_com_numeros():
    r = notas([risco(2), risco(4), risco(9.8)])
    assert r.justificativas[Face.frente] == ["Tela: De 3 a 5 riscos só rasante — 3 riscos só rasante (maior 9,8 mm) → B"]


def test_face_sem_defeito_e_todas_as_faces():
    r = notas([risco(6)])
    assert set(r.notas_por_face) == set(Face)
    assert r.notas_por_face[Face.traseira] == Nota.A
    assert r.justificativas[Face.traseira] == []


def test_rejeitado_nao_conta():
    assert notas([risco(16, estado=EstadoDefeito.rejeitado)]).nota_final == Nota.A


def test_mais_de_5_riscos_conta_por_face():  # L10
    r = notas([risco(1)] * 3 + [risco(1, face=Face.traseira, zona=Zona.vidro_traseiro)] * 3)
    assert r.notas_por_face[Face.frente] == Nota.B


# ---------------------------------------------------------------- margens e pendências


def test_margem_perto_do_limite_impede_automatico():
    r = notas([risco(5.3)])
    assert r.nota_final == Nota.B
    assert r.margem_minima == pytest.approx(0.06)
    assert not r.automatizavel


def test_longe_do_limite_e_automatizavel():
    r = notas([risco(9)])
    assert r.margem_minima > cr.MARGEM_AUTOMATICO
    assert r.automatizavel


def test_regra_a_definir_gera_pendencia():
    r = notas([D(face=Face.frente, tipo=TipoDefeito.lascado, zona=Zona.tela, visibilidade=V, maior_dimensao_mm=1)])
    assert r.nota_final == Nota.C
    assert any("a definir" in p for p in r.pendencias)
    assert not r.automatizavel


def test_anomalia_tratada_como_risco_e_revisao():  # R22, L8
    r = notas([D(face=Face.traseira, tipo=TipoDefeito.anomalia, zona=Zona.vidro_traseiro, visibilidade=V,
                 maior_dimensao_mm=4)])
    assert r.notas_por_face[Face.traseira] == Nota.C  # = risco visível
    assert any("anômala" in p for p in r.pendencias)


def test_tipo_sem_regra_vira_pendencia():
    r = notas([D(face=Face.frente, tipo=TipoDefeito.desgaste, zona=Zona.tela, visibilidade=V)])
    assert r.nota_final == Nota.A
    assert any("sem regra" in p for p in r.pendencias)


def test_marca_maior_que_3mm_na_moldura_a_definir():  # L5
    r = notas([risco(4, face=Face.lat_esq, zona=Zona.moldura)])
    assert r.nota_final == Nota.C and r.pendencias


# ---------------------------------------------------------------- propriedades (guia 16.5)

defeito = st.builds(
    D,
    face=st.sampled_from(list(Face)),
    tipo=st.sampled_from(list(TipoDefeito)),
    zona=st.sampled_from(list(Zona)),
    visibilidade=st.sampled_from(list(Visibilidade)),
    comprimento_mm=st.one_of(st.none(), st.floats(0.1, 60)),
    area_mm2=st.one_of(st.none(), st.floats(0.1, 200)),
    maior_dimensao_mm=st.one_of(st.none(), st.floats(0.1, 60)),
)
ORDEM = {Nota.A: 0, Nota.B: 1, Nota.C: 2, Nota.D: 3}


@settings(max_examples=300, deadline=None)
@given(st.lists(defeito, max_size=12), defeito)
def test_acrescentar_nunca_melhora(base, extra):
    antes, depois = notas(base), notas(base + [extra])
    assert ORDEM[depois.nota_final] >= ORDEM[antes.nota_final]
    for f in Face:
        assert ORDEM[depois.notas_por_face[f]] >= ORDEM[antes.notas_por_face[f]]


@settings(max_examples=200, deadline=None)
@given(st.lists(defeito, min_size=1, max_size=12), st.data())
def test_retirar_nunca_piora(base, data):
    i = data.draw(st.integers(0, len(base) - 1))
    menos = base[:i] + base[i + 1 :]
    assert ORDEM[notas(menos).nota_final] <= ORDEM[notas(base).nota_final]


@settings(max_examples=200, deadline=None)
@given(st.lists(defeito, max_size=12), st.randoms())
def test_ordem_nao_importa_e_deterministico(base, aleatorio):
    embaralhada = list(base)
    aleatorio.shuffle(embaralhada)
    a, b = notas(base), notas(embaralhada)
    assert a.notas_por_face == b.notas_por_face
    assert a.nota_final == b.nota_final
    assert sorted(a.pendencias) == sorted(b.pendencias)
    assert notas(base).como_dict() == a.como_dict()


# ---------------------------------------------------------------- validação do YAML


def _yaml():
    with open(cr.DIR_CRITERIOS / "criterio-v1.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_yaml_v1_valido():
    c = cr.carregar_versao("criterio-v1")
    assert c.versao == "criterio-v1"


def test_yaml_recusa_chave_desconhecida():
    y = _yaml()
    y["regras"]["tela"]["lista"][0]["peso"] = 2
    with pytest.raises(ValidationError):
        cr.Criterio.model_validate(y)


def test_yaml_recusa_enum_invalido():
    y = _yaml()
    y["regras"]["tela"]["lista"][0]["tipos"] = ["arranhao"]
    with pytest.raises(ValidationError):
        cr.Criterio.model_validate(y)


def test_yaml_recusa_regras_fora_de_ordem():
    y = _yaml()
    lista = y["regras"]["tela"]["lista"]
    lista[0], lista[-1] = lista[-1], lista[0]
    with pytest.raises(ValidationError, match="fora de ordem"):
        cr.Criterio.model_validate(y)


def test_yaml_recusa_zona_sem_grupo():
    y = copy.deepcopy(_yaml())
    y["grupos"]["moldura"].remove("porta")
    with pytest.raises(ValidationError, match="sem grupo"):
        cr.Criterio.model_validate(y)


def test_cadastro_de_modelos_coerente():
    from app.estetica import dimensoes

    ids = [i for m in dimensoes._LISTA for i in m.identificadores]
    assert len(ids) == len(set(ids)), "identificador repetido"
    for m in dimensoes._LISTA:
        assert 60 < m.largura_mm < 80 and 120 < m.altura_mm < 170 and 5 < m.espessura_mm < 9, m.nome
        assert m.tela in ("oled", "lcd") and m.moldura in ("aluminio", "aco", "titanio")
    assert dimensoes.MODELOS["iPhone18,4"].nome == "iPhone Air"
