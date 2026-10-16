"""Pipeline do worker com cenas sintéticas: aparelho num fundo escuro, fotos ambiente e rasante."""

import cv2
import numpy as np
import pytest
from sinteticos import desenhar_linha, retangulo_arredondado

from visao import fusao, pipeline

DIMS = {"largura": 71.5, "altura": 146.7, "espessura": 7.65}
PX = 15.0  # px/mm na foto
RISCOS = [((20, 40), (35, 40)), ((50, 100), (50, 110))]  # mm no referencial da face (topo em y = 0)


def _face(rasante: bool, ilha: bool, semente=0):
    rng = np.random.default_rng(semente)
    m = retangulo_arredondado(DIMS["largura"], DIMS["altura"], 9, PX).astype(np.float32)
    dentro = cv2.erode((m > 0.5).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    f = 0.06 * m + (0.30 if rasante else 0.18) * np.clip(m - dentro, 0, 1)
    if ilha:  # ilha de câmeras: canto superior esquerdo da traseira, com textura
        y0, x0 = int(6 * PX), int(6 * PX)
        bloco = rng.uniform(0.05, 0.6, (int(30 * PX), int(30 * PX))).astype(np.float32)
        f[y0:y0 + bloco.shape[0], x0:x0 + bloco.shape[1]] = cv2.GaussianBlur(bloco, (0, 0), 1.5)
    if rasante:
        for p0, p1 in RISCOS:
            desenhar_linha(f, p0, p1, PX, intensidade=0.15)
    return f, m


def _foto(rasante=False, ilha=False, girar_180=False, ang=3.0):
    f, m = _face(rasante, ilha)
    if girar_180:
        f, m = f[::-1, ::-1].copy(), m[::-1, ::-1].copy()
    H, W = 3000, 2400
    rot = cv2.getRotationMatrix2D((f.shape[1] / 2, f.shape[0] / 2), ang, 1.0)
    rot[:, 2] += [W / 2 - f.shape[1] / 2, H / 2 - f.shape[0] / 2]
    fundo = 0.03 + np.random.default_rng(1 + rasante).normal(0, 0.006, (H, W)).astype(np.float32)
    mw = cv2.warpAffine(m, rot, (W, H))
    img = fundo * (1 - mw) + cv2.warpAffine(f, rot, (W, H))
    ok, buf = cv2.imencode(".png", np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8))
    return buf.tobytes()


def _tarefa(face="frente", luz="rasante_a", **kw):
    return {
        "tarefa_id": "t1", "tipo": "foto", "sessao_id": "s1",
        "foto": {"foto_id": "f-" + luz, "passo": 1, "face": face, "faces": [face], "luz": luz, "pose": "deitado",
                 "lado": "tela_cima", "url": "mem://" + luz, "formato": "png", "metadados": {}},
        "fotos_irmas": [{"foto_id": "f-amb", "luz": "ambiente", "url": "mem://ambiente", "formato": "png"}],
        "aparelho": {"identificador": "iPhone14,5", "dimensoes_mm": DIMS, "raio_canto_mm": 9.0, "zonas_mm": {},
                     "familia": {}},
        "perfil_calibracao": {"orientacao": {"deitado": "topo_para_cima"}},
        "config": {"px_por_mm_retificacao": 20},
        "upload": {"retificada": {face: "mem://up/ret"}, "anotada": {face: "mem://up/anot"}},
    } | kw


@pytest.fixture(scope="module")
def fotos_frente():
    return {"mem://ambiente": _foto(), "mem://rasante_a": _foto(rasante=True)}


def test_frente_riscos_em_mm_no_referencial(fotos_frente):
    enviados = {}
    r = pipeline.processar_foto(_tarefa(), fotos_frente.__getitem__, enviados.__setitem__)
    assert r["qualidade"]["ok"], r["qualidade"]
    assert r["faces_extraidas"][0]["orientacao_ok"] is True
    assert r["artefatos"] == {"retificada": True, "anotada": True} and set(enviados) == {"mem://up/ret", "mem://up/anot"}
    assert len(r["deteccoes"]) == len(RISCOS)
    for (p0, p1) in RISCOS:
        real = float(np.hypot(p1[0] - p0[0], p1[1] - p0[1]))
        centro = (np.array(p0) + np.array(p1)) / 2
        d = min(r["deteccoes"], key=lambda d: np.linalg.norm(np.mean(d["geometria_mm"]["pontos"], axis=0) - centro))
        assert np.linalg.norm(np.mean(d["geometria_mm"]["pontos"], axis=0) - centro) < 1.0  # posição certa
        assert abs(d["comprimento_mm"] - real) <= max(0.05 * real, 0.5)
        assert d["zona"] == "tela" and d["tipo"] == "risco" and 0 <= d["confianca"] <= 1


def test_foto_ambiente_sem_deteccao(fotos_frente):
    r = pipeline.processar_foto(_tarefa(luz="ambiente", fotos_irmas=[]), fotos_frente.__getitem__)
    assert r["qualidade"]["ok"] and r["deteccoes"] == []


def test_sem_aparelho_reprova():
    vazio = cv2.imencode(".png", np.full((800, 600), 8, np.uint8))[1].tobytes()
    r = pipeline.processar_foto(_tarefa(luz="ambiente"), {"mem://ambiente": vazio}.__getitem__)
    assert r["qualidade"] == {"ok": False, "motivo": "contorno não encontrado", "contorno_ok": False}


def test_imagem_ilegivel_reprova():
    r = pipeline.processar_foto(_tarefa(luz="ambiente"), {"mem://ambiente": b"lixo"}.__getitem__)
    assert r["qualidade"]["ok"] is False and r["qualidade"]["motivo"].startswith("imagem ilegível")


def test_traseira_de_cabeca_para_baixo_e_corrigida():
    fotos = {"mem://ambiente": _foto(ilha=True, girar_180=True), "mem://rasante_a": _foto(True, True, girar_180=True)}
    r = pipeline.processar_foto(_tarefa(face="traseira"), fotos.__getitem__)
    assert r["faces_extraidas"][0]["orientacao_ok"] is True
    centro = (np.array(RISCOS[0][0]) + np.array(RISCOS[0][1])) / 2
    pos = [np.mean(d["geometria_mm"]["pontos"], axis=0) for d in r["deteccoes"]]
    assert min(np.linalg.norm(p - centro) for p in pos) < 1.0


def test_fusao_junta_o_mesmo_risco():
    risco = {"face": "frente", "fonte": "opencv_riscos", "tipo": "risco", "zona": "tela",
             "geometria_mm": {"tipo": "polilinha", "pontos": [[10, 10], [20, 10]]}, "caixa_mm": [10, 9.9, 10, 0.2],
             "comprimento_mm": 10.0, "contraste_rasante": 20, "contraste_ambiente": 2, "confianca": 0.8}
    deslocado = risco | {"geometria_mm": {"tipo": "polilinha", "pontos": [[10.3, 10.2], [21, 10.2]]},
                         "comprimento_mm": 10.7, "contraste_rasante": 30, "contraste_ambiente": 8}
    outro = risco | {"geometria_mm": {"tipo": "polilinha", "pontos": [[10, 50], [12, 50]]}, "caixa_mm": [10, 50, 2, 0.1],
                     "comprimento_mm": 2.0}
    ok = {"ok": True}
    t = {"tarefa_id": "t9", "tipo": "fusao", "sessao_id": "s1",
         "roteiro": {"passos": [{"faces": ["frente", "lat_esq"]}, {"faces": ["traseira"]}]},
         "fotos": [
             {"foto_id": "a", "resultado": {"qualidade": ok, "faces_extraidas": [{"face": "frente"}], "deteccoes": [risco, outro]}},
             {"foto_id": "b", "resultado": {"qualidade": ok, "faces_extraidas": [{"face": "frente"}], "deteccoes": [deslocado]}},
             {"foto_id": "c", "resultado": {"qualidade": {"ok": False}, "faces_extraidas": [{"face": "traseira"}]}},
         ]}
    r = fusao.fundir_sessao(t)
    assert len(r["defeitos"]) == 2
    grande = max(r["defeitos"], key=lambda d: d["comprimento_mm"])
    assert grande["comprimento_mm"] == 10.7 and grande["fotos"] == ["a", "b"] and grande["foto_principal"] == "b"
    assert grande["visibilidade"] == "visivel"  # contraste na ambiente 8 ≥ T_VISIVEL
    assert min(r["defeitos"], key=lambda d: d["comprimento_mm"])["visibilidade"] == "so_rasante"
    assert r["faces_sem_foto_valida"] == ["lat_esq", "traseira"]


def test_zonas_prioridade():
    from visao import zonas

    rot = zonas.mapa("traseira", DIMS, 9.0, {"traseira": {"ilha_camera": [[5, 5, 30, 30]], "lente_camera": [[8, 8, 10, 10]]}}, 10)
    assert zonas.zona_de(rot, np.array([[100, 100]])) == "lente_camera"
    assert zonas.zona_de(rot, np.array([[300, 300]])) == "ilha_camera"
    assert zonas.zona_de(rot, np.array([[350, 800]])) == "vidro_traseiro"
    assert zonas.zona_de(rot, np.array([[2, 800]])) == "moldura"
    assert zonas.zona_de(rot, np.array([[2, 2]])) == "quina"
