import io
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from PIL import Image
from sqlalchemy import select

from app.estetica import retencao
from app.estetica.armazenamento import armazenamento
from app.estetica.modelos import FotoEstetica
from tests.conftest import Loja_, defeito, fluxo_ate_sugestao

FACES = {f: "A" for f in ("frente", "traseira", "lat_esq", "lat_dir", "topo", "base")}


def _caminho(url):
    u = urlparse(url)
    return u.path + "?" + u.query


def test_url_assinada(cliente):
    arm = armazenamento()
    arm.salvar("teste/a.jpg", b"\xff\xd8\xffdados", "image/jpeg")
    url = arm.url_leitura("teste/a.jpg")
    assert cliente.get(_caminho(url)).content == b"\xff\xd8\xffdados"
    adulterada = _caminho(url).replace("teste/a.jpg", "teste/b.jpg")
    assert cliente.get(adulterada).status_code == 403
    put = arm.url_escrita("teste/c.jpg", "image/jpeg")
    assert cliente.put(_caminho(put), content=b"novo").status_code == 201
    assert arm.ler("teste/c.jpg") == b"novo"
    q = parse_qs(urlparse(url).query)
    assert cliente.put(f"/arquivos/teste/a.jpg?op=get&exp={q['exp'][0]}&sig={q['sig'][0]}", content=b"x").status_code == 403


def test_laudo_e_verificacao(cliente, db):
    l = Loja_(cliente, db)
    s, reg = fluxo_ate_sugestao(cliente, l, [defeito(comp=6)])
    # retificada da frente com luz ambiente, como o worker enviaria
    foto = db.scalar(select(FotoEstetica).where(FotoEstetica.sessao_id == s.id, FotoEstetica.luz == "ambiente",
                                                FotoEstetica.passo == 1))
    foto.chave_retificada = f"sessoes/{s.id}/retificada/{foto.id}"
    db.commit()
    buf = io.BytesIO()
    Image.new("RGB", (1430, 2934), (30, 30, 30)).save(buf, "JPEG")
    armazenamento().salvar(f"{foto.chave_retificada}_frente.jpg", buf.getvalue(), "image/jpeg")
    d = cliente.get(f"/estetica/sessoes/{s.id}", headers=l.h_tecnico).json()
    corpo = {"sessao_id": str(s.id), "notas_por_face": d["sugestao"]["notas_por_face"], "nota_final": "B"}
    assert cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico, json=corpo).status_code == 201
    b = cliente.get(f"/laudo/{reg.id}/estetica", headers=l.h_tecnico).json()
    assert b["nota_final"] == "B" and b["origem"] == "sugerida"
    assert b["defeitos"][0]["medida"] == "6,0 mm" and set(b["miniaturas"]) == {"frente"}
    mini = cliente.get(_caminho(b["miniaturas"]["frente"])).content
    assert max(Image.open(io.BytesIO(mini)).size) == 480
    html = cliente.get(f"/laudo/{reg.id}/estetica?formato=html", headers=l.h_tecnico).text
    assert "Estado estético" in html and "Nota <strong>B</strong>" in html
    pub = cliente.get(f"/verificar/{reg.id}/estetica").json()
    assert "original" not in str(pub) and pub["nota_final"] == "B"


def test_retencao(cliente, db):
    l = Loja_(cliente, db)
    s, reg = fluxo_ate_sugestao(cliente, l, [defeito(comp=6, foto_principal=None)])
    fotos = db.scalars(select(FotoEstetica).where(FotoEstetica.sessao_id == s.id)).all()
    d = cliente.get(f"/estetica/sessoes/{s.id}", headers=l.h_tecnico).json()
    # o técnico desenha um defeito numa foto específica: essa foto fica
    guardada = fotos[0]
    novo = {"novo": {"face": "frente", "tipo": "risco", "zona": "tela", "visibilidade": "so_rasante",
                     "caixa_mm": [1, 1, 2, 1], "comprimento_mm": 2, "foto_id": str(guardada.id)}}
    corpo = {"sessao_id": str(s.id), "notas_por_face": d["sugestao"]["notas_por_face"], "nota_final": "B",
             "defeitos": [novo]}
    assert cliente.post(f"/registros/{reg.id}/estetica", headers=l.h_tecnico, json=corpo).status_code == 201
    daqui_2_anos = datetime.now(timezone.utc) + timedelta(days=800)
    assert retencao.rodar(simular=True, agora=daqui_2_anos)["apagadas"] == 5
    r = retencao.rodar(agora=daqui_2_anos)
    assert r == {"apagadas": 5, "mantidas_com_defeito": 1, "simulado": False}
    db.expire_all()
    assert not armazenamento().existe(fotos[1].chave) and armazenamento().existe(guardada.chave)
    assert retencao.rodar(agora=daqui_2_anos)["apagadas"] == 0
