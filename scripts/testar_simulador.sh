#!/usr/bin/env bash
# Teste do app no simulador contra o backend de desenvolvimento (sem iPhone):
#  1. tela QR + preto do aparelho avaliado: long-poll e comando "preto" vindo da cabine;
#  2. pareamento da cabine pelo app (código gerado como admin).
# Capturas em ~/.morecheck/testes/. Pré-requisitos: Xcode com a plataforma iOS e um simulador.
#
#   scripts/testar_simulador.sh ["iPhone 16 Pro"]
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
SIM="${1:-iPhone 16 Pro}"
SAIDA="$HOME/.morecheck/testes"; DD="$RAIZ/app-ios/build"
mkdir -p "$SAIDA"
API=http://127.0.0.1:8000
TOKENS="$HOME/.morecheck/dev-tokens.json"
campo() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$1" "$2"; }

curl -sf "$API/saude" >/dev/null || "$RAIZ/scripts/subir_dev.sh" --nulo >/dev/null

echo "→ compilando o app"
(cd "$RAIZ/app-ios" && xcodegen generate >/dev/null && xcodebuild -project Morecheck.xcodeproj -scheme Morecheck \
  -destination "platform=iOS Simulator,name=$SIM" -derivedDataPath "$DD" build 2>&1 | grep -E "error:|BUILD" )
APP="$DD/Build/Products/Debug-iphonesimulator/Morecheck.app"

echo "→ simulador $SIM"
xcrun simctl boot "$SIM" 2>/dev/null || true
for _ in $(seq 1 90); do xcrun simctl list devices booted | grep -q "$SIM" && break; sleep 2; done
xcrun simctl install "$SIM" "$APP"

echo "→ 1. tela QR + preto"
SESSAO="$(cd "$RAIZ/backend" && uv run python -m app.dev sessao --dados "$TOKENS")"
TOKEN=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['token_sessao'])" "$SESSAO")
xcrun simctl terminate "$SIM" com.morecheck.app 2>/dev/null || true
xcrun simctl launch "$SIM" com.morecheck.app -testeTela qr -testeApi "$API" -testeToken "$TOKEN" >/dev/null
sleep 5; xcrun simctl io "$SIM" screenshot "$SAIDA/1-qr.png" >/dev/null 2>&1
curl -sf -X POST "$API/cabine/$TOKEN/tela" -H "Authorization: Bearer $(campo "$TOKENS" token_cabine)" \
  -H 'Content-Type: application/json' -d '{"acao":"preto"}' >/dev/null
sleep 4; xcrun simctl io "$SIM" screenshot "$SAIDA/2-preto.png" >/dev/null 2>&1
python3 - "$SAIDA/1-qr.png" "$SAIDA/2-preto.png" <<'PY'
import sys
from PIL import Image
qr, preto = (Image.open(p).convert("L") for p in sys.argv[1:3])
m = lambda im: sum(im.getdata()) / (im.width * im.height)
print(f"   brilho médio: QR {m(qr):.0f} → preto {m(preto):.0f}")
assert m(qr) > 120 and m(preto) < 10, "a tela não ficou preta"
print("   OK: o aparelho avaliado apagou a tela pelo comando da cabine")
PY

echo "→ 2. pareamento da cabine"
CODIGO=$(curl -sf -X POST "$API/cabines/pareamento" -H "Authorization: Bearer $(campo "$TOKENS" token_admin)" | python3 -c "import json,sys;print(json.load(sys.stdin)['codigo'])")
xcrun simctl terminate "$SIM" com.morecheck.app 2>/dev/null || true
xcrun simctl launch "$SIM" com.morecheck.app -testeTela cabine -testeApi "$API" -testeCodigo "$CODIGO" >/dev/null
sleep 6; xcrun simctl io "$SIM" screenshot "$SAIDA/3-cabine.png" >/dev/null 2>&1
curl -sf "$API/cabines" -H "Authorization: Bearer $(campo "$TOKENS" token_admin)" | python3 -c "
import json,sys; c=[x for x in json.load(sys.stdin) if x['nome']=='Cabine simulador']
assert c, 'cabine do simulador não apareceu no backend'
print('   OK: cabine pareada pelo app:', c[-1]['cabine_id'][:8])"
echo "Capturas em $SAIDA"
