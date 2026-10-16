from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..base.autenticacao import usuario_atual
from ..base.modelos import Registro, Sessao, Usuario
from ..db import obter_db
from . import estetica

rotas = APIRouter(tags=["laudo"])


def _registro(db, registro_id) -> Registro:
    r = db.get(Registro, registro_id)
    if r is None:
        raise HTTPException(404, "Registro inexistente")
    return r


@rotas.get("/laudo/{registro_id}/estetica")
def bloco(registro_id: str, formato: str = "json", usuario: Usuario = Depends(usuario_atual),
          db: Session = Depends(obter_db)):
    r = _registro(db, registro_id)
    if db.get(Sessao, r.sessao_id).loja_id != usuario.loja_id:
        raise HTTPException(404, "Registro inexistente")
    dados = estetica.bloco(db, r.sessao_id)
    if dados is None:
        raise HTTPException(404, "Sem avaliação estética")
    return HTMLResponse(estetica.html_bloco(dados)) if formato == "html" else dados


@rotas.get("/verificar/{registro_id}/estetica")
def verificacao_publica(registro_id: str, db: Session = Depends(obter_db)):
    """Página pública do QR do laudo (D11): miniaturas + defeitos; sem fotos originais."""
    r = _registro(db, registro_id)
    dados = estetica.bloco(db, r.sessao_id)
    if dados is None:
        raise HTTPException(404, "Sem avaliação estética")
    return {k: dados[k] for k in ("nota_final", "origem_texto", "notas_por_face", "versao_criterio", "miniaturas",
                                  "defeitos", "avaliada_em")}
