"""Rotas da cabine (guia 7.3) e pareamento (D10)."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..base import auditoria
from ..base.autenticacao import admin_atual
from ..base.modelos import Usuario
from ..db import obter_db
from . import eventos, sessoes
from .esquemas import Ativar, Concluir, PedidoTela
from .modelos import Cabine, CodigoPareamento
from .seguranca import cabine_atual, hash_segredo, novo_codigo_pareamento, novo_token

rotas = APIRouter(tags=["cabine"])
VALIDADE_CODIGO = timedelta(minutes=10)


@rotas.get("/cabine/{token}")
def abrir(token: str, refazer: int = 0, cabine: Cabine = Depends(cabine_atual), db: Session = Depends(obter_db)):
    return sessoes.abrir(db, cabine, token, bool(refazer))


@rotas.post("/cabine/{token}/fotos", status_code=201)
async def enviar_foto(
    token: str,
    passo: int = Form(...),
    face: str = Form(...),
    luz: str = Form(...),
    pose: str = Form(...),
    lado: str | None = Form(None),
    tentativa: int = Form(1),
    metadados: str = Form(...),
    arquivo: UploadFile = File(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    cabine: Cabine = Depends(cabine_atual),
    db: Session = Depends(obter_db),
):
    meta = sessoes.ler_metadados(metadados)
    formato = (meta.get("formato") or "").lower()
    dados = await arquivo.read()
    campos = {"passo": passo, "face": face, "luz": luz, "pose": pose, "lado": lado, "tentativa": tentativa,
              "metadados": meta, "formato": formato}
    return sessoes.receber_foto(db, cabine, token, idempotency_key, campos, dados)


@rotas.post("/cabine/{token}/concluir", status_code=202)
def concluir(token: str, corpo: Concluir, cabine: Cabine = Depends(cabine_atual), db: Session = Depends(obter_db)):
    return sessoes.concluir(db, cabine, token, corpo.fotos_enviadas)


@rotas.post("/cabine/{token}/tela", status_code=202)
def tela(token: str, corpo: PedidoTela, cabine: Cabine = Depends(cabine_atual), db: Session = Depends(obter_db)):
    sessoes.pedir_tela(db, cabine, token, corpo.acao)
    return {"ok": True}


@rotas.get("/cabine/{token}/sugestao")
def sugestao(token: str, cabine: Cabine = Depends(cabine_atual), db: Session = Depends(obter_db)):
    return sessoes.estado_sugestao(db, cabine, token)


@rotas.get("/cabine/{token}/eventos")
async def eventos_cabine(token: str, apos: int = 0, cabine: Cabine = Depends(cabine_atual),
                         db: Session = Depends(obter_db)):
    """Eventos para a cabine (foto_reprovada, sugestao_pronta), mesmo formato de 7.4."""
    sessao = sessoes.sessao_por_token(db, token)
    if sessao.loja_id != cabine.loja_id:
        raise HTTPException(404, "Sessão inexistente ou expirada")
    db.close()
    return {"eventos": await eventos.aguardar(sessao.id, apos, ("foto_reprovada", "sugestao_pronta"))}


@rotas.put("/cabine/perfil")
async def perfil(request: Request, cabine: Cabine = Depends(cabine_atual), db: Session = Depends(obter_db)):
    """Perfil de calibração atual da cabine (guia 7.11); vai junto em cada tarefa do worker."""
    sessoes.salvar_perfil(db, cabine, await request.json())
    return {"ok": True}


# ---------------------------------------------------------------- pareamento (D10)


@rotas.post("/cabines/pareamento", status_code=201)
def criar_codigo(usuario: Usuario = Depends(admin_atual), db: Session = Depends(obter_db)):
    codigo = novo_codigo_pareamento()
    expira = datetime.now(timezone.utc) + VALIDADE_CODIGO
    db.add(CodigoPareamento(loja_id=usuario.loja_id, codigo_hash=hash_segredo(codigo), criado_por=usuario.id,
                            expira_em=expira))
    auditoria.registrar(db, "usuario", usuario.id, "estetica.pareamento_criado", "loja", usuario.loja_id)
    db.commit()
    return {"codigo": codigo, "expira_em": expira.isoformat()}


@rotas.post("/cabines/ativar", status_code=201)
def ativar(corpo: Ativar, db: Session = Depends(obter_db)):
    c = db.scalar(
        select(CodigoPareamento).where(CodigoPareamento.codigo_hash == hash_segredo(corpo.codigo.strip().upper()))
        .with_for_update()
    )
    if c is None or c.usado_em is not None or c.expira_em < datetime.now(timezone.utc):
        raise HTTPException(400, "Código de pareamento inválido ou expirado")
    token = novo_token()
    cab = Cabine(loja_id=c.loja_id, nome=corpo.nome, token_hash=hash_segredo(token))
    db.add(cab)
    c.usado_em = datetime.now(timezone.utc)
    db.flush()
    auditoria.registrar(db, "cabine", cab.id, "estetica.cabine_ativada", "cabine", cab.id, nome=corpo.nome)
    db.commit()
    return {"cabine_id": str(cab.id), "token": token}  # o token só aparece aqui; o backend guarda o hash


@rotas.get("/cabines")
def listar(usuario: Usuario = Depends(admin_atual), db: Session = Depends(obter_db)):
    cabs = db.scalars(select(Cabine).where(Cabine.loja_id == usuario.loja_id).order_by(Cabine.criada_em)).all()
    return [{"cabine_id": str(c.id), "nome": c.nome, "ativa": c.ativa, "criada_em": c.criada_em.isoformat(),
             "perfil_versao": (c.perfil_calibracao or {}).get("versao")} for c in cabs]


@rotas.post("/cabines/{cabine_id}/revogar")
def revogar(cabine_id: str, usuario: Usuario = Depends(admin_atual), db: Session = Depends(obter_db)):
    cab = db.get(Cabine, cabine_id)
    if cab is None or cab.loja_id != usuario.loja_id:
        raise HTTPException(404, "Cabine inexistente")
    cab.ativa = False
    cab.revogada_em = datetime.now(timezone.utc)
    auditoria.registrar(db, "usuario", usuario.id, "estetica.cabine_revogada", "cabine", cab.id)
    db.commit()
    return {"ok": True}
