#!/usr/bin/env bash
# Simula um aparelho passando pela cabine, contra o ambiente de scripts/subir_dev.sh.
#
#   scripts/simular_aparelho.sh                         # fotos sintéticas (gabarito conhecido)
#   scripts/simular_aparelho.sh <pasta> <n> [modelo]    # suas fotos no padrão da fase 0 (ap{n}_frente_amb.jpg…)
#   ex.: scripts/simular_aparelho.sh visao/prototipos/fotos 2 iPhone14,5
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
TOKENS="$HOME/.morecheck/dev-tokens.json"
[ -f "$TOKENS" ] || { echo "Rode scripts/subir_dev.sh antes."; exit 1; }
PASTA="${1:-}"; N="${2:-1}"; MODELO="${3:-iPhone14,5}"
TMP="$(mktemp -d -t morecheck-sim)"
if [ -z "$PASTA" ]; then
  (cd "$RAIZ/visao" && uv run python -I ferramentas/gerar_sinteticas.py "$TMP/fotos" >/dev/null)
  PASTA="$TMP/fotos"
else
  PASTA="$(cd "$PASTA" && pwd)"
fi
(cd "$RAIZ/backend" && uv run python -m app.dev sessao --dados "$TOKENS" --modelo "$MODELO") >"$TMP/sessao.json"
(cd "$RAIZ/visao" && uv run python -I ferramentas/simular_cabine.py --api http://127.0.0.1:8000 \
  --dados "$TOKENS" --sessao "$TMP/sessao.json" --fotos "$PASTA" --aparelho "$N")
echo "Abra o painel para avaliar: http://127.0.0.1:8000/painel/"
