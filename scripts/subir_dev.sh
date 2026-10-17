#!/usr/bin/env bash
# Sobe o ambiente de desenvolvimento: Postgres (banco morecheck_dev), backend com o painel em
# /painel e o worker de visão. Configuração em ~/.morecheck/desenvolvimento.env.
#
#   scripts/subir_dev.sh            # só neste Mac (127.0.0.1:8000)
#   scripts/subir_dev.sh --rede     # acessível na rede local pelo nome .local do Mac (iPhone)
#   scripts/subir_dev.sh --rede --ip  # idem, pelo IP (se o iPhone não achar o nome .local)
#   scripts/subir_dev.sh --nulo     # worker nulo (sem visão)
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
CASA="$HOME/.morecheck"
RUN="$CASA/run"; LOGS="$CASA/logs"; TOKENS="$CASA/dev-tokens.json"
mkdir -p "$RUN" "$LOGS"
PORTA=8000; HOST=127.0.0.1; NULO=""; USAR_IP=0
for a in "$@"; do case "$a" in --rede) HOST=0.0.0.0 ;; --ip) USAR_IP=1 ;; --nulo) NULO="--nulo" ;; esac; done

if [ -f "$RUN/backend.pid" ] && kill -0 "$(cat "$RUN/backend.pid")" 2>/dev/null; then
  echo "Já está no ar. Para reiniciar: scripts/parar_dev.sh && scripts/subir_dev.sh"; exit 0
fi
[ -f "$CASA/desenvolvimento.env" ] || { echo "Falta $CASA/desenvolvimento.env (ver docs/passo-a-passo.md)"; exit 1; }

URL="http://127.0.0.1:$PORTA"
if [ "$HOST" = 0.0.0.0 ]; then
  # Nome .local (mDNS): o iOS aceita HTTP para .local (NSAllowsLocalNetworking), não para IP.
  URL="http://$(scutil --get LocalHostName).local:$PORTA"
  if [ $USAR_IP = 1 ]; then
    URL="http://$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1):$PORTA"
  fi
fi
export URL_PUBLICA="$URL" MORECHECK_API_URL="http://127.0.0.1:$PORTA"

echo "→ banco"
pg_isready -q || { echo "Postgres não está rodando (brew services start postgresql@15)"; exit 1; }
createdb morecheck_dev 2>/dev/null || true
(cd "$RAIZ/backend" && uv run alembic upgrade head >"$LOGS/migracao.log" 2>&1)

if [ ! -f "$TOKENS" ]; then
  echo "→ dados iniciais (loja, técnico, admin, cabine)"
  (cd "$RAIZ/backend" && uv run python -m app.dev semear) >"$TOKENS"
  chmod 600 "$TOKENS"
fi

if [ ! -f "$RAIZ/painel/dist/index.html" ] || [ -n "$(find "$RAIZ/painel/src" -newer "$RAIZ/painel/dist/index.html" -print -quit)" ]; then
  echo "→ build do painel"
  (cd "$RAIZ/painel" && { [ -d node_modules ] || npm install --silent; } && npm run build >"$LOGS/painel-build.log" 2>&1)
fi

echo "→ backend ($URL)"
(cd "$RAIZ/backend" && exec uv run uvicorn app.main:app --host "$HOST" --port "$PORTA" >>"$LOGS/backend.log" 2>&1) &
echo $! >"$RUN/backend.pid"
for _ in $(seq 1 40); do curl -sf "http://127.0.0.1:$PORTA/saude" >/dev/null && break; sleep 0.5; done
curl -sf "http://127.0.0.1:$PORTA/saude" >/dev/null || { echo "Backend não subiu: veja $LOGS/backend.log"; exit 1; }

echo "→ worker de visão ${NULO:-real}"
(cd "$RAIZ/visao" && exec uv run python -m visao.worker $NULO >>"$LOGS/worker.log" 2>&1) &
echo $! >"$RUN/worker.pid"

python3 - "$TOKENS" "$URL" <<'PY'
import json, sys
t = json.load(open(sys.argv[1])); url = sys.argv[2]
print(f"""
Pronto.
  Painel:  {url}/painel/
  API:     {url}/docs   (no app do iPhone, use: {url})
  Token do técnico: {t['token_tecnico']}
  Token do admin:   {t['token_admin']}
  Logs:    ~/.morecheck/logs/   ·   Parar: scripts/parar_dev.sh
  Testar um aparelho: scripts/simular_aparelho.sh""")
PY
