#!/usr/bin/env bash
# Faz o papel da cabine: manda o aparelho avaliado apagar a tela, mostrar o QR ou voltar ao normal.
#   scripts/comando_tela.sh <token_da_sessao> preto|qr|normal
set -euo pipefail
TOKEN="${1:?uso: comando_tela.sh <token> preto|qr|normal}"; ACAO="${2:-preto}"
CAB=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.morecheck/dev-tokens.json')))['token_cabine'])")
curl -sf -X POST "http://127.0.0.1:8000/cabine/$TOKEN/tela" -H "Authorization: Bearer $CAB" \
  -H 'Content-Type: application/json' -d "{\"acao\":\"$ACAO\"}" >/dev/null && echo "enviado: $ACAO"
