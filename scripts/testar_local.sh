#!/usr/bin/env bash
# Teste ponta a ponta local, sem fotos reais: banco de desenvolvimento → backend → worker →
# cabine simulada (fotos sintéticas) → sugestão → painel (API). Desliga tudo no fim.
#
#   scripts/testar_local.sh            # worker real (camada a)
#   scripts/testar_local.sh --nulo     # worker nulo (fase 3)
#   scripts/testar_local.sh --manter   # deixa backend e worker no ar para abrir o painel
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d -t morecheck-e2e)"
PORTA=8765
NULO=""; MANTER=0
for a in "$@"; do case "$a" in --nulo) NULO="--nulo" ;; --manter) MANTER=1 ;; esac; done

export DATABASE_URL="postgresql+psycopg://localhost/morecheck_dev"
export URL_PUBLICA="http://127.0.0.1:$PORTA" ESTETICA_DIR_FOTOS="$TMP/storage"
export VISAO_WORKER_TOKENS="tok-local" ESTETICA_SEGREDO_URLS="segredo-local"
export MORECHECK_API_URL="http://127.0.0.1:$PORTA" VISAO_WORKER_TOKEN="tok-local" VISAO_WORKER_ID="local"

PIDS=()
matar_arvore() {  # o processo e todos os descendentes (uv → python)
  local p="$1" filho
  for filho in $(pgrep -P "$p" 2>/dev/null); do matar_arvore "$filho"; done
  kill "$p" 2>/dev/null || true
}
encerrar() { for p in "${PIDS[@]:-}"; do [ -n "$p" ] && matar_arvore "$p"; done; }
[ "$MANTER" = 1 ] || trap encerrar EXIT

echo "→ banco morecheck_dev"
createdb morecheck_dev 2>/dev/null || true
(cd "$RAIZ/backend" && uv run alembic upgrade head >/dev/null 2>&1)

echo "→ backend em http://127.0.0.1:$PORTA (log: $TMP/backend.log)"
(cd "$RAIZ/backend" && uv run uvicorn app.main:app --host 127.0.0.1 --port $PORTA >"$TMP/backend.log" 2>&1) &
PIDS+=($!)
for _ in $(seq 1 30); do curl -sf "http://127.0.0.1:$PORTA/saude" >/dev/null && break; sleep 0.5; done

echo "→ worker ${NULO:-real} (log: $TMP/worker.log)"
(cd "$RAIZ/visao" && uv run python -m visao.worker $NULO >"$TMP/worker.log" 2>&1) &
PIDS+=($!)

echo "→ dados de desenvolvimento e fotos sintéticas"
(cd "$RAIZ/backend" && uv run python -m app.dev semear >"$TMP/dev.json" \
  && uv run python -m app.dev sessao --dados "$TMP/dev.json" >"$TMP/sessao.json")
(cd "$RAIZ/visao" && uv run python -I ferramentas/gerar_sinteticas.py "$TMP/fotos" >/dev/null)

echo "→ cabine simulada"
(cd "$RAIZ/visao" && uv run python -I ferramentas/simular_cabine.py --api "http://127.0.0.1:$PORTA" \
  --dados "$TMP/dev.json" --sessao "$TMP/sessao.json" --fotos "$TMP/fotos" --aparelho 1)

TOKEN=$(python3 -c "import json;print(json.load(open('$TMP/dev.json'))['token_tecnico'])")
echo
echo "Token do técnico (para entrar no painel): $TOKEN"
if [ "$MANTER" = 1 ]; then
  echo "Backend e worker continuam no ar (PIDs ${PIDS[*]}). Painel:"
  echo "  cd painel && MORECHECK_API=http://127.0.0.1:$PORTA npm run dev"
  echo "Para desligar: pkill -f 'uvicorn app.main:app --host 127.0.0.1 --port $PORTA'; pkill -f visao.worker"
fi
