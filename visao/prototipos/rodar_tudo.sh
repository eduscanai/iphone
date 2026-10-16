#!/usr/bin/env bash
# Roda a análise da fase 0 na ordem (guia 8.3). Uso: prototipos/rodar_tudo.sh [altura_mm]
set -euo pipefail
cd "$(dirname "$0")/.."
ALTURA="${1:-250}"
py() { uv run python -I "$@"; }
py prototipos/conferir_fotos.py
py prototipos/medir_escala.py --altura-mm "$ALTURA"
py prototipos/riscos.py
py prototipos/comparar_iluminacao.py
py prototipos/comparar_resolucao.py
py prototipos/profundidade_foco.py
py prototipos/cruzar_anotacao.py
py prototipos/relatorio.py --altura-mm "$ALTURA"
