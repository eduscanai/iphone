"""Configuração por variáveis de ambiente (guia 7.12).

Produção: segredos só em ~/.morecheck/producao.env. Desenvolvimento: ~/.morecheck/desenvolvimento.env
ou variáveis de ambiente. Nunca imprimir valores de segredos.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# O último arquivo vence: se os dois existirem, produção vence desenvolvimento.
ARQUIVOS_ENV = (
    Path.home() / ".morecheck" / "desenvolvimento.env",
    Path.home() / ".morecheck" / "producao.env",
)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=ARQUIVOS_ENV, env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/morecheck_dev"
    url_publica: str = "http://localhost:8000"  # base das URLs assinadas no modo disco

    # Armazenamento das fotos (D8)
    estetica_armazenamento: str = "disco"  # disco ou s3
    estetica_dir_fotos: Path = Path.home() / ".morecheck" / "fotos-dev"
    s3_endpoint_url: str | None = None
    s3_bucket_estetica: str = "morecheck-estetica"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    estetica_segredo_urls: str = Field(default="dev-troque-em-producao", repr=False)

    estetica_tamanho_max_mb: int = 40
    estetica_retencao_meses: int = 12
    estetica_url_expira_s: int = 900

    # Roteiro e luzes (D1, D3, D4)
    estetica_roteiro: str = "roteiro-v1"  # roteiro-v1 (espelhos) ou roteiro-v1-em-pe
    estetica_contraluz: bool = False
    estetica_rasante_juntas: bool = False  # True = uma foto rasante_ab

    # Fila e eventos
    estetica_lease_s: int = 120
    estetica_tentativas_max: int = 3
    estetica_long_poll_s: float = 25.0
    estetica_long_poll_intervalo_s: float = 0.5
    estetica_px_por_mm_retificacao: int = 20
    estetica_versao_pipeline_minima: str = "0.1.0"

    # Gate do modo automático (fase 5)
    estetica_kappa_tecnicos: float | None = None  # linha de base da fase 1
    estetica_percentual_holdout: int = 10  # % dos aparelhos (por hash do IMEI) no conjunto de teste

    visao_worker_tokens: str = Field(default="", repr=False)  # lista separada por vírgula
    painel_dir: Path | None = None  # build do painel servido em /painel (padrão: painel/dist do repositório)

    @property
    def tokens_worker(self) -> list[str]:
        return [t.strip() for t in self.visao_worker_tokens.split(",") if t.strip()]


@lru_cache
def config() -> Config:
    return Config()
