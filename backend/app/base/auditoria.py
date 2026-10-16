from sqlalchemy.orm import Session

from .modelos import Auditoria


def registrar(db: Session, ator_tipo: str, ator_id, acao: str, entidade: str, entidade_id=None, **dados):
    """Grava na auditoria (sem commit: vai junto com a transação de quem chamou).
    Nunca passar segredos em `dados`."""
    db.add(
        Auditoria(
            ator_tipo=ator_tipo,
            ator_id=str(ator_id) if ator_id else None,
            acao=acao,
            entidade=entidade,
            entidade_id=str(entidade_id) if entidade_id else None,
            dados={k: (str(v) if not isinstance(v, (int, float, bool, str, list, dict, type(None))) else v)
                   for k, v in dados.items()},
        )
    )
