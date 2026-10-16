from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import config


class Base(DeclarativeBase):
    pass


_engine = None
_fabrica = None


def engine():
    global _engine, _fabrica
    if _engine is None:
        _engine = create_engine(config().database_url, pool_pre_ping=True)
        _fabrica = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def nova_sessao() -> Session:
    engine()
    return _fabrica()


def obter_db() -> Iterator[Session]:
    db = nova_sessao()
    try:
        yield db
    finally:
        db.close()


def reiniciar_engine():
    """Para os testes, depois de trocar DATABASE_URL."""
    global _engine, _fabrica
    if _engine is not None:
        _engine.dispose()
    _engine = _fabrica = None
