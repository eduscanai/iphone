"""Testes contra Postgres real (SKIP LOCKED, JSONB, CHECK). Banco: morecheck_teste
(createdb morecheck_teste). A migração roda do zero no início da sessão de testes."""

import io
import json
import os
import uuid

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://localhost/morecheck_teste")
os.environ["VISAO_WORKER_TOKENS"] = "tok-worker-1,tok-worker-2"
os.environ["ESTETICA_LONG_POLL_S"] = "1"
os.environ["ESTETICA_LONG_POLL_INTERVALO_S"] = "0.05"
os.environ["ESTETICA_KAPPA_TECNICOS"] = "0.8"
os.environ["ESTETICA_SEGREDO_URLS"] = "segredo-de-teste"
os.environ["URL_PUBLICA"] = "http://testserver"

from alembic import command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import config as modulo_config  # noqa: E402
from app import db as modulo_db  # noqa: E402
from app.base.autenticacao import hash_token  # noqa: E402
from app.base.modelos import Loja, Registro, Sessao, Usuario  # noqa: E402
from app.estetica import armazenamento as modulo_arm  # noqa: E402
from app.estetica.modelos import ConfigEsteticaLoja  # noqa: E402

WORKER = {"Authorization": "Bearer tok-worker-1"}
TABELAS = ["config_estetica_loja", "evento_sessao", "defeito_estetico", "avaliacao_estetica", "sugestao_estetica",
           "tarefa_visao", "foto_estetica", "sessao_estetica", "cabine_pareamento", "cabine", "auditoria", "registro",
           "sessao", "usuario", "loja"]


@pytest.fixture(scope="session", autouse=True)
def banco(tmp_path_factory):
    os.environ["ESTETICA_DIR_FOTOS"] = str(tmp_path_factory.mktemp("fotos"))
    modulo_config.config.cache_clear()
    modulo_db.reiniciar_engine()
    modulo_arm.reiniciar()
    cfg = AlembicConfig("alembic.ini")
    cfg.attributes["url"] = os.environ["DATABASE_URL"]
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def limpar():
    with modulo_db.engine().begin() as c:
        c.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db():
    s = modulo_db.nova_sessao()
    yield s
    s.close()


@pytest.fixture
def cliente():
    from app.main import app

    return TestClient(app)


class Loja_:
    """Uma loja com técnico, admin, cabine pareada e uma sessão de aparelho."""

    def __init__(self, cliente, db, modo="assistido", percentual_cego=0, modelo="iPhone14,5", imei="356000000000001"):
        self.cliente = cliente
        self.loja = Loja(id=uuid.uuid4(), nome="Loja teste")
        db.add(self.loja)
        db.flush()
        self.tecnico_token, self.admin_token = f"tec-{uuid.uuid4()}", f"adm-{uuid.uuid4()}"
        self.tecnico = Usuario(id=uuid.uuid4(), loja_id=self.loja.id, nome="Técnico", papel="tecnico",
                               token_hash=hash_token(self.tecnico_token))
        self.admin = Usuario(id=uuid.uuid4(), loja_id=self.loja.id, nome="Admin", papel="admin",
                             token_hash=hash_token(self.admin_token))
        db.add_all([self.tecnico, self.admin,
                     ConfigEsteticaLoja(loja_id=self.loja.id, modo=modo, percentual_cego=percentual_cego)])
        db.commit()
        codigo = cliente.post("/cabines/pareamento", headers=self.h_admin).json()["codigo"]
        r = cliente.post("/cabines/ativar", json={"codigo": codigo, "nome": "Cabine 1"}).json()
        self.cabine_id, self.cabine_token = r["cabine_id"], r["token"]
        self.db = db
        self.modelo, self.imei = modelo, imei

    @property
    def h_tecnico(self):
        return {"Authorization": f"Bearer {self.tecnico_token}"}

    @property
    def h_admin(self):
        return {"Authorization": f"Bearer {self.admin_token}"}

    @property
    def h_cabine(self):
        return {"Authorization": f"Bearer {self.cabine_token}"}

    def nova_sessao(self, modelo=None, imei=None):
        s = Sessao(id=uuid.uuid4(), loja_id=self.loja.id, token=f"tk-{uuid.uuid4().hex[:12]}",
                   identificador_modelo=modelo or self.modelo, cor="meia-noite", imei=imei or self.imei)
        self.db.add(s)
        self.db.flush()
        reg = Registro(id=uuid.uuid4(), sessao_id=s.id)
        self.db.add(reg)
        self.db.commit()
        return s, reg


def jpeg(tamanho=(64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", tamanho, (20, 20, 20)).save(buf, "JPEG")
    return buf.getvalue()


def metadados(**extra) -> str:
    m = {"camera": {"modelo": "iPhone15,3", "lente": "grande_angular_1x", "app_versao": "1.8.0"},
         "exposicao": {"duracao_s": 1 / 60, "iso": 125.0}, "foco": {"lens_position": 0.62},
         "balanco_branco": {"r": 1.92, "g": 1.0, "b": 1.71}, "dimensoes_px": {"largura": 64, "altura": 48},
         "formato": "jpeg", "rotacao_graus": 0, "perfil_calibracao_versao": 1,
         "capturada_em": "2026-10-20T14:03:11.402-03:00",
         "qualidade_local": {"nitidez": 812.4, "estouro_pct": 0.02, "contorno_ok": True}}
    m.update(extra)
    return json.dumps(m)


def enviar_foto(cliente, l: Loja_, token, passo, luz, chave=None, face=None, pose="deitado", dados=None, **meta):
    face = face or ("frente" if passo == 1 else "traseira")
    return cliente.post(
        f"/cabine/{token}/fotos",
        headers=l.h_cabine | {"Idempotency-Key": chave or str(uuid.uuid4())},
        data={"passo": passo, "face": face, "luz": luz, "pose": pose, "tentativa": 1, "metadados": metadados(**meta)},
        files={"arquivo": ("f.jpg", dados if dados is not None else jpeg(), "image/jpeg")},
    )


LUZES = ["ambiente", "rasante_a", "rasante_b"]


def capturar_tudo(cliente, l: Loja_, token):
    for passo in (1, 2):
        for luz in LUZES:
            assert enviar_foto(cliente, l, token, passo, luz).status_code == 201
    assert cliente.post(f"/cabine/{token}/concluir", headers=l.h_cabine, json={"fotos_enviadas": 6}).status_code == 202


def processar_fotos(cliente, ok=True):
    """Worker fajuto: aprova (ou reprova) todas as fotos pendentes."""
    n = 0
    while True:
        r = cliente.post("/visao/tarefas/reservar", headers=WORKER, json={"worker_id": "w1", "tipos": ["foto"]})
        if r.status_code == 204:
            return n
        t = r.json()
        faces = t["foto"]["faces"]
        corpo = {"tarefa_id": t["tarefa_id"], "tipo": "foto", "foto_id": t["foto"]["foto_id"], "versao_visao": "0.1.0",
                 "qualidade": {"ok": ok, "motivo": None if ok else "tremida"},
                 "faces_extraidas": [{"face": f} for f in faces], "deteccoes": [], "artefatos": {}, "tempo_ms": 5}
        assert cliente.post(f"/visao/tarefas/{t['tarefa_id']}/resultado", headers=WORKER, json=corpo).status_code == 200
        n += 1


def defeito(face="frente", tipo="risco", zona="tela", vis="so_rasante", comp=6.0, **kw):
    return {"face": face, "tipo": tipo, "zona": zona, "visibilidade": vis, "caixa_mm": [10, 10, 5, 1],
            "comprimento_mm": comp, "maior_dimensao_mm": comp, "confianca": 0.9, "fonte": "opencv_riscos"} | kw


def fundir(cliente, defeitos=(), sem_foto=()):
    r = cliente.post("/visao/tarefas/reservar", headers=WORKER, json={"worker_id": "w1", "tipos": ["fusao"]})
    assert r.status_code == 200, r.text
    t = r.json()
    corpo = {"tarefa_id": t["tarefa_id"], "tipo": "fusao", "sessao_id": t["sessao_id"], "versao_visao": "0.1.0",
             "modelos": {}, "defeitos": list(defeitos), "faces_sem_foto_valida": list(sem_foto), "tempo_ms": 3}
    r = cliente.post(f"/visao/tarefas/{t['tarefa_id']}/resultado", headers=WORKER, json=corpo)
    assert r.status_code == 200, r.text
    return t


def fluxo_ate_sugestao(cliente, l: Loja_, defeitos=(), modelo=None, imei=None):
    s, reg = l.nova_sessao(modelo=modelo, imei=imei)
    assert cliente.get(f"/cabine/{s.token}", headers=l.h_cabine).status_code == 200
    capturar_tudo(cliente, l, s.token)
    processar_fotos(cliente)
    fundir(cliente, defeitos)
    return s, reg
