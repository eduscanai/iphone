"""Cliente da API do worker (guia 7.6). O worker puxa tarefas por HTTPS (R14)."""

import os

import httpx


class ClienteAPI:
    def __init__(self, url: str | None = None, token: str | None = None, worker_id: str | None = None,
                 timeout: float = 60.0, transporte=None):
        self.url = (url or os.environ.get("MORECHECK_API_URL", "http://localhost:8000")).rstrip("/")
        token = token or os.environ.get("VISAO_WORKER_TOKEN", "")
        self.worker_id = worker_id or os.environ.get("VISAO_WORKER_ID", "worker-local")
        self.http = httpx.Client(base_url=self.url, timeout=timeout, transport=transporte,
                                 headers={"Authorization": f"Bearer {token}"})
        # URLs assinadas (fotos, uploads) não levam o token do worker
        self.arquivos = httpx.Client(timeout=timeout, transport=transporte)

    def reservar(self, tipos=("foto", "fusao")) -> dict | None:
        r = self.http.post("/visao/tarefas/reservar", json={"worker_id": self.worker_id, "tipos": list(tipos)})
        if r.status_code == 204:
            return None
        r.raise_for_status()
        return r.json()

    def renovar(self, tarefa_id: str) -> None:
        self.http.post(f"/visao/tarefas/{tarefa_id}/renovar", json={"worker_id": self.worker_id}).raise_for_status()

    def resultado(self, tarefa_id: str, corpo: dict) -> None:
        self.http.post(f"/visao/tarefas/{tarefa_id}/resultado", json=corpo).raise_for_status()

    def falha(self, tarefa_id: str, erro: str, recuperavel: bool = True) -> None:
        self.http.post(f"/visao/tarefas/{tarefa_id}/falha",
                       json={"erro": erro[:4000], "recuperavel": recuperavel, "worker_id": self.worker_id}).raise_for_status()

    def baixar(self, url: str) -> bytes:
        r = self.arquivos.get(url)
        r.raise_for_status()
        return r.content

    def enviar(self, url: str, dados: bytes, tipo: str = "image/jpeg") -> None:
        self.arquivos.put(url, content=dados, headers={"Content-Type": tipo}).raise_for_status()
