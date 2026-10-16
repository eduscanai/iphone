from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import config

from .estetica import rotas_arquivos, rotas_cabine, rotas_pagina, rotas_painel, rotas_visao
from .laudo import rotas as rotas_laudo

app = FastAPI(title="Morecheck — nota estética", version="0.1.0")
for r in (rotas_cabine.rotas, rotas_pagina.rotas, rotas_visao.rotas, rotas_painel.rotas, rotas_arquivos.rotas,
          rotas_laudo.rotas):
    app.include_router(r)


@app.get("/saude")
def saude():
    return {"ok": True}


# Painel compilado (npm run build) no mesmo servidor: sem CORS, e o QR de pareamento já sai
# com a URL da API (window.location.origin).
_painel = config().painel_dir or Path(__file__).resolve().parents[2] / "painel" / "dist"
if (_painel / "index.html").exists():
    app.mount("/painel", StaticFiles(directory=_painel, html=True), name="painel")

    @app.get("/", include_in_schema=False)
    def raiz():
        return RedirectResponse("/painel/")
