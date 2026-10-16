from fastapi import FastAPI

from .estetica import rotas_arquivos, rotas_cabine, rotas_pagina, rotas_painel, rotas_visao
from .laudo import rotas as rotas_laudo

app = FastAPI(title="Morecheck — nota estética", version="0.1.0")
for r in (rotas_cabine.rotas, rotas_pagina.rotas, rotas_visao.rotas, rotas_painel.rotas, rotas_arquivos.rotas,
          rotas_laudo.rotas):
    app.include_router(r)


@app.get("/saude")
def saude():
    return {"ok": True}
