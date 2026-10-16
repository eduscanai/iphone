#!/usr/bin/env bash
# Gera include/segredos.h (fora do Git) com o Wi-Fi da loja e a chave das luzes, que vem de
# ~/.morecheck/producao.env ou desenvolvimento.env (CABINE_LUZ_CHAVE): a mesma que vai no app.
#
#   hardware/cabine-luz/configurar.sh "<nome da rede>" [n_cabine]
# A senha do Wi-Fi é pedida sem aparecer na tela (ou venha em WIFI_SENHA).
set -euo pipefail
cd "$(dirname "$0")"
SSID="${1:?uso: configurar.sh \"<nome da rede>\" [n_cabine]}"
N="${2:-1}"
CHAVE=""
for f in "$HOME/.morecheck/producao.env" "$HOME/.morecheck/desenvolvimento.env"; do
  [ -f "$f" ] && CHAVE="$(grep -E '^CABINE_LUZ_CHAVE=' "$f" | head -1 | cut -d= -f2-)" && [ -n "$CHAVE" ] && break
done
[ -n "$CHAVE" ] || { echo "CABINE_LUZ_CHAVE não encontrada em ~/.morecheck/*.env"; exit 1; }
if [ -z "${WIFI_SENHA:-}" ]; then read -r -s -p "Senha do Wi-Fi \"$SSID\": " WIFI_SENHA; echo; fi
umask 077
cat > include/segredos.h <<H
// Gerado por configurar.sh — NÃO versionar (está no .gitignore).
#pragma once
#define WIFI_SSID "$SSID"
#define WIFI_SENHA "$WIFI_SENHA"
#define CHAVE_CABINE "$CHAVE"
#define NOME_MDNS "morecheck-cabine-$N"
H
echo "include/segredos.h criado (cabine $N, rede \"$SSID\")."
echo "Gravar: uvx --from platformio pio run -t upload   ·   Monitor: uvx --from platformio pio device monitor"
