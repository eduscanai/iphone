#!/usr/bin/env bash
# Prepara o app para instalar no SEU iPhone: grava app-ios/Config/Local.xcconfig (fora do Git) com o
# seu time e um bundle ID único, gera o projeto e abre o Xcode.
#   scripts/preparar_iphone.sh <TEAM_ID> [bundle_id]
#   ex.: scripts/preparar_iphone.sh ABCDE12345 com.maria.morecheck
# O TEAM_ID está em Xcode → Settings → Accounts (conta gratuita serve: "Personal Team").
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
TEAM="${1:-}"
if [ -z "$TEAM" ]; then
  echo "Uso: scripts/preparar_iphone.sh <TEAM_ID> [bundle_id]"
  echo "Certificados de desenvolvimento neste Mac (o código entre parênteses NÃO é o Team ID, mas ajuda a achar a conta):"
  security find-identity -v -p codesigning 2>/dev/null | grep "Apple Development" || echo "  nenhum: entre com seu Apple ID em Xcode → Settings → Accounts"
  exit 1
fi
BUNDLE="${2:-com.$(id -un | tr -cd 'a-z0-9').morecheck}"
cat >"$RAIZ/app-ios/Config/Local.xcconfig" <<X
// Gerado por scripts/preparar_iphone.sh — fora do Git.
DEVELOPMENT_TEAM = $TEAM
PRODUCT_BUNDLE_IDENTIFIER = $BUNDLE
X
(cd "$RAIZ/app-ios" && xcodegen generate >/dev/null)
echo "Time $TEAM · bundle $BUNDLE"
echo "No Xcode: escolha o seu iPhone no topo e aperte ⌘R. No iPhone, na primeira vez:"
echo "  Ajustes → Privacidade e Segurança → Modo de Desenvolvedor (ligar e reiniciar)"
echo "  Ajustes → Geral → VPN e Gerenciamento de Dispositivos → confiar no seu Apple ID"
open "$RAIZ/app-ios/Morecheck.xcodeproj"
