#!/usr/bin/env bash
# Cria uma sessão de aparelho no ambiente de desenvolvimento e mostra o QR na tela do Mac, para o
# iPhone em modo Cabine ler (faz o papel do aparelho avaliado mostrando o QR).
#   scripts/nova_sessao.sh [modelo]      # padrão iPhone14,5 (iPhone 13). Ex.: iPhone16,1 (15 Pro)
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
MODELO="${1:-iPhone14,5}"
SAIDA="$HOME/.morecheck/testes"; mkdir -p "$SAIDA"
J="$(cd "$RAIZ/backend" && uv run python -m app.dev sessao --dados "$HOME/.morecheck/dev-tokens.json" --modelo "$MODELO")"
TOKEN=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['token_sessao'])" "$J")
PNG="$SAIDA/qr-$TOKEN.png"
(cd "$RAIZ/visao" && uv run python -c "
import cv2, numpy as np, sys
q = cv2.QRCodeEncoder.create().encode(sys.argv[1])
q = cv2.copyMakeBorder(q, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
cv2.imwrite(sys.argv[2], cv2.resize(q, None, fx=24, fy=24, interpolation=cv2.INTER_NEAREST))" "$TOKEN" "$PNG")
echo "Sessão criada (modelo $MODELO). Token: $TOKEN"
echo "QR: $PNG"
open "$PNG"
