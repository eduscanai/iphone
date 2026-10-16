"""Arquivos no modo disco: GET/PUT por URL assinada (HMAC + validade). No modo s3 não é usado."""

from fastapi import APIRouter, HTTPException, Request, Response

from ..config import config
from .armazenamento import armazenamento, assinatura_valida

rotas = APIRouter(tags=["arquivos"])
TIPOS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".heic": "image/heic", ".dng": "image/x-adobe-dng",
         ".png": "image/png"}


def _validar(op: str, chave: str, exp: int, sig: str):
    if config().estetica_armazenamento != "disco":
        raise HTTPException(404, "Indisponível")
    if not assinatura_valida(op, chave, exp, sig):
        raise HTTPException(403, "URL inválida ou expirada")


@rotas.get("/arquivos/{chave:path}")
def ler(chave: str, op: str, exp: int, sig: str):
    _validar(op if op == "get" else "x", chave, exp, sig)
    if not armazenamento().existe(chave):
        raise HTTPException(404, "Arquivo inexistente")
    tipo = next((t for ext, t in TIPOS.items() if chave.lower().endswith(ext)), "application/octet-stream")
    return Response(armazenamento().ler(chave), media_type=tipo)


@rotas.put("/arquivos/{chave:path}", status_code=201)
async def escrever(chave: str, op: str, exp: int, sig: str, request: Request):
    _validar(op if op == "put" else "x", chave, exp, sig)
    dados = await request.body()
    if len(dados) > config().estetica_tamanho_max_mb * 1024 * 1024:
        raise HTTPException(413, "Arquivo grande demais")
    armazenamento().salvar(chave, dados, request.headers.get("content-type", "application/octet-stream"))
    return {"ok": True}
