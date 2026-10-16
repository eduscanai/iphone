"""Armazenamento das fotos (guia 11.1 passo 4; D8): `disco` (desenvolvimento) ou `s3` (R2/S3).

Interface: salvar, ler, url_leitura, url_escrita, apagar. No modo disco, as URLs apontam
para o próprio backend (/arquivos/…) com assinatura HMAC e validade.
"""

import hashlib
import hmac
import time
from pathlib import Path
from urllib.parse import quote, urlencode

from ..config import config


class Armazenamento:
    def salvar(self, chave: str, dados: bytes, tipo: str) -> None: ...
    def ler(self, chave: str) -> bytes: ...
    def url_leitura(self, chave: str, expira_s: int | None = None) -> str: ...
    def url_escrita(self, chave: str, tipo: str, expira_s: int | None = None) -> str: ...
    def apagar(self, chave: str) -> None: ...
    def existe(self, chave: str) -> bool: ...


def assinar(operacao: str, chave: str, expira: int) -> str:
    msg = f"{operacao}\n{chave}\n{expira}".encode()
    return hmac.new(config().estetica_segredo_urls.encode(), msg, hashlib.sha256).hexdigest()


def assinatura_valida(operacao: str, chave: str, expira: int, assinatura: str) -> bool:
    return expira >= time.time() and hmac.compare_digest(assinar(operacao, chave, expira), assinatura)


class Disco(Armazenamento):
    def __init__(self, raiz: Path):
        self.raiz = Path(raiz)

    def _caminho(self, chave: str) -> Path:
        p = (self.raiz / chave).resolve()
        if self.raiz.resolve() not in p.parents:
            raise ValueError("chave fora do diretório de fotos")
        return p

    def salvar(self, chave, dados, tipo):
        p = self._caminho(chave)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(dados)
        tmp.replace(p)

    def ler(self, chave):
        return self._caminho(chave).read_bytes()

    def existe(self, chave):
        return self._caminho(chave).exists()

    def _url(self, op, chave, expira_s):
        expira = int(time.time()) + (expira_s or config().estetica_url_expira_s)
        q = urlencode({"op": op, "exp": expira, "sig": assinar(op, chave, expira)})
        return f"{config().url_publica.rstrip('/')}/arquivos/{quote(chave)}?{q}"

    def url_leitura(self, chave, expira_s=None):
        return self._url("get", chave, expira_s)

    def url_escrita(self, chave, tipo, expira_s=None):
        return self._url("put", chave, expira_s)

    def apagar(self, chave):
        self._caminho(chave).unlink(missing_ok=True)


class S3(Armazenamento):
    def __init__(self):
        import boto3

        c = config()
        self.bucket = c.s3_bucket_estetica
        self.cliente = boto3.client(
            "s3",
            endpoint_url=c.s3_endpoint_url,
            aws_access_key_id=c.s3_access_key_id,
            aws_secret_access_key=c.s3_secret_access_key,
            region_name="auto",
        )

    def salvar(self, chave, dados, tipo):
        self.cliente.put_object(Bucket=self.bucket, Key=chave, Body=dados, ContentType=tipo)

    def ler(self, chave):
        return self.cliente.get_object(Bucket=self.bucket, Key=chave)["Body"].read()

    def existe(self, chave):
        try:
            self.cliente.head_object(Bucket=self.bucket, Key=chave)
            return True
        except self.cliente.exceptions.ClientError:
            return False

    def url_leitura(self, chave, expira_s=None):
        return self.cliente.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": chave},
            ExpiresIn=expira_s or config().estetica_url_expira_s)

    def url_escrita(self, chave, tipo, expira_s=None):
        return self.cliente.generate_presigned_url(
            "put_object", Params={"Bucket": self.bucket, "Key": chave, "ContentType": tipo},
            ExpiresIn=expira_s or config().estetica_url_expira_s)

    def apagar(self, chave):
        self.cliente.delete_object(Bucket=self.bucket, Key=chave)


_instancia: Armazenamento | None = None


def armazenamento() -> Armazenamento:
    global _instancia
    if _instancia is None:
        c = config()
        _instancia = S3() if c.estetica_armazenamento == "s3" else Disco(c.estetica_dir_fotos)
    return _instancia


def reiniciar():
    global _instancia
    _instancia = None


TIPOS_MIME = {"heic": "image/heic", "jpeg": "image/jpeg", "dng": "image/x-adobe-dng"}
