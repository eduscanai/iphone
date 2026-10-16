"""Fila de tarefas de visão em Postgres (guia R14, 11.1 passo 6).

Reserva com SELECT … FOR UPDATE SKIP LOCKED, prazo (lease) configurável (padrão 120 s) e
até 3 tentativas. Regras de liberação:
- tarefa `foto` de luz não ambiente só sai depois que a foto `ambiente` do mesmo passo chegou;
- tarefa `fusao` só sai com a sessão concluída e nenhuma tarefa `foto` pendente ou reservada.
Fusões têm prioridade (a meta de 10 s conta a partir da última foto).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ..config import config
from .enums import StatusTarefa, TipoTarefa
from .modelos import TarefaVisao


def agora() -> datetime:
    return datetime.now(timezone.utc)


def criar(db: Session, tipo: TipoTarefa, sessao_id: uuid.UUID, foto_id: uuid.UUID | None = None) -> TarefaVisao:
    t = TarefaVisao(tipo=str(tipo), sessao_id=sessao_id, foto_id=foto_id, status=StatusTarefa.pendente)
    db.add(t)
    return t


def _recolher_vencidas(db: Session) -> None:
    db.execute(
        text("""
            UPDATE tarefa_visao
               SET status = CASE WHEN tentativas >= :max THEN 'falhou' ELSE 'pendente' END,
                   erro = CASE WHEN tentativas >= :max THEN 'prazo de reserva vencido' ELSE erro END,
                   worker_id = NULL, reservada_ate = NULL, atualizada_em = now()
             WHERE status = 'reservada' AND reservada_ate < now()
        """),
        {"max": config().estetica_tentativas_max},
    )


_SQL_PROXIMA = text("""
    SELECT t.id
      FROM tarefa_visao t
      LEFT JOIN foto_estetica f ON f.id = t.foto_id
      LEFT JOIN sessao_estetica s ON s.sessao_id = t.sessao_id
     WHERE t.status = 'pendente'
       AND t.tipo = ANY(:tipos)
       AND (t.tipo <> 'foto' OR f.luz = 'ambiente' OR EXISTS (
             SELECT 1 FROM foto_estetica a
              WHERE a.sessao_id = f.sessao_id AND a.passo = f.passo AND a.luz = 'ambiente'))
       AND (t.tipo <> 'fusao' OR (s.concluida_em IS NOT NULL AND NOT EXISTS (
             SELECT 1 FROM tarefa_visao o
              WHERE o.sessao_id = t.sessao_id AND o.tipo = 'foto' AND o.status IN ('pendente', 'reservada'))))
     ORDER BY (t.tipo = 'fusao') DESC, t.criada_em
     LIMIT 1
       FOR UPDATE OF t SKIP LOCKED
""")


def reservar(db: Session, worker_id: str, tipos: list[str]) -> TarefaVisao | None:
    """Reserva e devolve a próxima tarefa (já com commit), ou None."""
    _recolher_vencidas(db)
    db.commit()
    linha = db.execute(_SQL_PROXIMA, {"tipos": tipos}).first()
    if linha is None:
        db.rollback()
        return None
    t = db.get(TarefaVisao, linha.id)
    t.status = StatusTarefa.reservada
    t.tentativas += 1
    t.worker_id = worker_id
    t.reservada_ate = agora() + timedelta(seconds=config().estetica_lease_s)
    t.atualizada_em = agora()
    db.commit()
    return t


def renovar(db: Session, tarefa: TarefaVisao, worker_id: str) -> bool:
    if tarefa.status != StatusTarefa.reservada or tarefa.worker_id != worker_id:
        return False
    tarefa.reservada_ate = agora() + timedelta(seconds=config().estetica_lease_s)
    tarefa.atualizada_em = agora()
    return True


def concluir(tarefa: TarefaVisao, resultado: dict) -> None:
    tarefa.status = StatusTarefa.concluida
    tarefa.resultado = resultado
    tarefa.reservada_ate = None
    tarefa.atualizada_em = agora()


def falhar(tarefa: TarefaVisao, erro: str, recuperavel: bool) -> None:
    """Recuperável volta para a fila até esgotar as tentativas."""
    tarefa.erro = erro[:2000]
    tarefa.reservada_ate = None
    tarefa.worker_id = None
    tarefa.atualizada_em = agora()
    if recuperavel and tarefa.tentativas < config().estetica_tentativas_max:
        tarefa.status = StatusTarefa.pendente
    else:
        tarefa.status = StatusTarefa.falhou


def pendentes_da_sessao(db: Session, sessao_id, tipo: str | None = None) -> list[TarefaVisao]:
    q = select(TarefaVisao).where(
        TarefaVisao.sessao_id == sessao_id, TarefaVisao.status.in_([StatusTarefa.pendente, StatusTarefa.reservada])
    )
    if tipo:
        q = q.where(TarefaVisao.tipo == tipo)
    return list(db.scalars(q))


def idade_da_mais_antiga_s(db: Session) -> float | None:
    """Para o alerta de worker parado (fila > 5 min, guia 19)."""
    v = db.scalar(text("SELECT EXTRACT(EPOCH FROM now() - min(criada_em)) FROM tarefa_visao WHERE status = 'pendente'"))
    return float(v) if v is not None else None


def cancelar_fusoes_pendentes(db: Session, sessao_id) -> None:
    db.execute(
        update(TarefaVisao)
        .where(TarefaVisao.sessao_id == sessao_id, TarefaVisao.tipo == TipoTarefa.fusao,
               TarefaVisao.status == StatusTarefa.pendente)
        .values(status=StatusTarefa.falhou, erro="substituída por nova captura", atualizada_em=agora())
    )
