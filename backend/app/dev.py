"""Dados de desenvolvimento (STUB: no Morecheck real, usar o mecanismo de teste do backend).

    uv run python -m app.dev semear                 # loja, técnico, admin, cabine pareada
    uv run python -m app.dev sessao --dados d.json  # nova sessão de aparelho + registro

Imprime JSON com os tokens. Só para banco de desenvolvimento.
"""

import argparse
import json
import secrets
import uuid
from pathlib import Path

from .base.autenticacao import hash_token
from .base.modelos import Loja, Registro, Sessao, Usuario
from .db import nova_sessao
from .estetica.modelos import Cabine, ConfigEsteticaLoja
from .estetica.seguranca import hash_segredo, novo_token


def semear(modo: str, percentual_cego: float) -> dict:
    with nova_sessao() as db:
        loja = Loja(id=uuid.uuid4(), nome="Loja de desenvolvimento")
        db.add(loja)
        db.flush()
        tec, adm, cab = (secrets.token_urlsafe(16) for _ in range(3))
        db.add_all([
            Usuario(id=uuid.uuid4(), loja_id=loja.id, nome="Técnico dev", papel="tecnico", token_hash=hash_token(tec)),
            Usuario(id=uuid.uuid4(), loja_id=loja.id, nome="Admin dev", papel="admin", token_hash=hash_token(adm)),
            ConfigEsteticaLoja(loja_id=loja.id, modo=modo, percentual_cego=percentual_cego),
        ])
        cab = novo_token()
        cabine = Cabine(loja_id=loja.id, nome="Cabine dev", token_hash=hash_segredo(cab))
        db.add(cabine)
        db.commit()
        return {"loja_id": str(loja.id), "token_tecnico": tec, "token_admin": adm, "token_cabine": cab,
                "cabine_id": str(cabine.id)}


def nova_sessao_aparelho(loja_id: str, modelo: str, cor: str, imei: str | None) -> dict:
    with nova_sessao() as db:
        s = Sessao(id=uuid.uuid4(), loja_id=loja_id, token=secrets.token_urlsafe(12), identificador_modelo=modelo,
                   cor=cor, imei=imei or str(uuid.uuid4().int)[:15])
        db.add(s)
        db.flush()
        r = Registro(id=uuid.uuid4(), sessao_id=s.id)
        db.add(r)
        db.commit()
        return {"sessao_id": str(s.id), "token_sessao": s.token, "registro_id": str(r.id)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("semear")
    a.add_argument("--modo", default="assistido")
    a.add_argument("--percentual-cego", type=float, default=0)
    b = sub.add_parser("sessao")
    b.add_argument("--dados", type=Path, required=True, help="JSON gerado por `semear`")
    b.add_argument("--modelo", default="iPhone14,5")
    b.add_argument("--cor", default="meia-noite")
    b.add_argument("--imei")
    args = ap.parse_args()
    if args.cmd == "semear":
        print(json.dumps(semear(args.modo, args.percentual_cego), indent=2))
    else:
        d = json.loads(args.dados.read_text())
        print(json.dumps(nova_sessao_aparelho(d["loja_id"], args.modelo, args.cor, args.imei), indent=2))
