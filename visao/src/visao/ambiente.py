"""Lê ~/.morecheck/desenvolvimento.env e ~/.morecheck/producao.env (guia, regra 4) para o
ambiente do processo, sem sobrescrever variáveis já definidas no shell. Nunca imprime valores."""

import os
from pathlib import Path

ARQUIVOS = (Path.home() / ".morecheck" / "producao.env", Path.home() / ".morecheck" / "desenvolvimento.env")


def carregar(arquivos=ARQUIVOS) -> list[Path]:
    lidos = []
    for arq in arquivos:  # produção primeiro: se as duas existirem, produção vence
        if not arq.exists():
            continue
        for linha in arq.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))
        lidos.append(arq)
    return lidos
