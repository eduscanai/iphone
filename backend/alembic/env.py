from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.config import config as app_config

cfg = context.config
if cfg.config_file_name:
    fileConfig(cfg.config_file_name)

url = cfg.attributes.get("url") or app_config().database_url


def rodar_offline():
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def rodar_online():
    with create_engine(url).connect() as conexao:
        context.configure(connection=conexao)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    rodar_offline()
else:
    rodar_online()
