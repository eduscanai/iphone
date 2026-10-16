"""Worker de visão (guia 12.2): puxa tarefas do backend, processa e devolve o resultado.

    uv run python -m visao.worker            # real
    uv run python -m visao.worker --nulo     # qualidade ok, sem geometria nem defeitos (fase 3)
    uv run python -m visao.worker --uma-vez  # processa o que houver e sai

Configuração (guia 7.12): MORECHECK_API_URL, VISAO_WORKER_TOKEN, VISAO_WORKER_ID,
VISAO_DISPOSITIVO (cpu, mps ou cuda; usado quando houver detector/PatchCore).
"""

import argparse
import json
import logging
import sys
import threading
import time
from datetime import datetime, timezone

import httpx

from . import config, fusao, pipeline
from . import modelos as reg_modelos
from .cliente_api import ClienteAPI

log = logging.getLogger("visao.worker")


def registrar(**campos):
    campos = {"quando": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
              "versao": config.VERSAO_PIPELINE} | campos
    log.info(json.dumps(campos, ensure_ascii=False))


def resultado_nulo(t: dict) -> dict:
    if t["tipo"] == "foto":
        return {"tarefa_id": t["tarefa_id"], "tipo": "foto", "foto_id": t["foto"]["foto_id"],
                "versao_visao": f"{config.VERSAO_PIPELINE}-nulo", "qualidade": {"ok": True},
                "faces_extraidas": [{"face": f} for f in t["foto"].get("faces", [t["foto"]["face"]])],
                "deteccoes": [], "artefatos": {}, "tempo_ms": 0}
    return {"tarefa_id": t["tarefa_id"], "tipo": "fusao", "sessao_id": t["sessao_id"],
            "versao_visao": f"{config.VERSAO_PIPELINE}-nulo", "modelos": {}, "defeitos": [],
            "faces_sem_foto_valida": [], "tempo_ms": 0}


class Renovador:
    """Renova a reserva a cada 60 s enquanto a tarefa roda (tarefas longas)."""

    def __init__(self, cliente: ClienteAPI, tarefa_id: str):
        self.cliente, self.tarefa_id = cliente, tarefa_id
        self.parar = threading.Event()
        self.thread = threading.Thread(target=self._rodar, daemon=True)

    def _rodar(self):
        while not self.parar.wait(config.RENOVAR_A_CADA_S):
            try:
                self.cliente.renovar(self.tarefa_id)
            except httpx.HTTPError as e:
                registrar(tarefa_id=self.tarefa_id, evento="falha_renovar", erro=str(e))

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.parar.set()


def processar(cliente: ClienteAPI, t: dict, nulo: bool, modelos=None) -> None:
    t0 = time.monotonic()
    try:
        with Renovador(cliente, t["tarefa_id"]):
            if nulo:
                r = resultado_nulo(t)
            elif t["tipo"] == "foto":
                r = pipeline.processar_foto(t, cliente.baixar, cliente.enviar, modelos)
            else:
                r = fusao.fundir_sessao(t, modelos.descricao if modelos else None)
        cliente.resultado(t["tarefa_id"], r)
        registrar(tarefa_id=t["tarefa_id"], tipo=t["tipo"], evento="concluida",
                  ms=int((time.monotonic() - t0) * 1000), ok=r.get("qualidade", {}).get("ok", True),
                  deteccoes=len(r.get("deteccoes", r.get("defeitos", []))))
    except httpx.HTTPError as e:  # rede ou backend: tenta de novo depois
        registrar(tarefa_id=t["tarefa_id"], evento="erro_rede", erro=str(e))
        _falha(cliente, t, f"rede: {e}", recuperavel=True)
    except Exception as e:  # noqa: BLE001 — exceção inesperada vira falha da tarefa (guia 12.2)
        registrar(tarefa_id=t["tarefa_id"], evento="erro", erro=repr(e))
        _falha(cliente, t, repr(e), recuperavel=True)


def _falha(cliente, t, erro, recuperavel):
    try:
        cliente.falha(t["tarefa_id"], erro, recuperavel)
    except httpx.HTTPError as e:
        registrar(tarefa_id=t["tarefa_id"], evento="falha_ao_reportar", erro=str(e))


def laco(cliente: ClienteAPI, nulo=False, uma_vez=False, tipos=("foto", "fusao"), modelos=None) -> int:
    espera, feitas = 1.0, 0
    while True:
        try:
            t = cliente.reservar(tipos)
        except httpx.HTTPError as e:
            registrar(evento="erro_reservar", erro=str(e))
            t = None
            if uma_vez:
                return feitas
        if t is None:
            if uma_vez:
                return feitas
            time.sleep(espera)
            espera = min(espera * 1.5, 5.0)
            continue
        espera = 1.0
        processar(cliente, t, nulo, modelos)
        feitas += 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nulo", action="store_true")
    ap.add_argument("--uma-vez", action="store_true")
    ap.add_argument("--tipos", default="foto,fusao")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # sem uma linha por consulta à fila
    modelos = None if args.nulo else reg_modelos.carregar()  # uma vez, mantidos em memória (12.2)
    if modelos is not None:
        registrar(evento="modelos", **(modelos.descricao or {"camadas": "só (a)"}))
    feitas = laco(ClienteAPI(), args.nulo, args.uma_vez, tuple(args.tipos.split(",")), modelos)
    registrar(evento="fim", tarefas=feitas)


if __name__ == "__main__":
    main()
