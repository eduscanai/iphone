#!/usr/bin/env bash
# Prepara o ambiente de desenvolvimento num Mac novo (colaborador). Pode rodar de novo sem problema.
#   scripts/configurar_dev.sh            # confere, gera ~/.morecheck/desenvolvimento.env, instala dependências
#   scripts/configurar_dev.sh --instalar # também instala com Homebrew o que faltar
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
INSTALAR=0; [ "${1:-}" = "--instalar" ] && INSTALAR=1
falta=()
tem() { command -v "$1" >/dev/null 2>&1; }
conferir() {  # comando, pacote do brew
  if tem "$1"; then echo "  ok  $1"; else echo "  --  $1 (brew install $2)"; falta+=("$2"); fi
}
echo "→ ferramentas"
tem brew || { echo "Instale o Homebrew: https://brew.sh"; exit 1; }
conferir uv uv
conferir node node
conferir psql postgresql@15
conferir xcodegen xcodegen
xcode-select -p >/dev/null 2>&1 && echo "  ok  Xcode" || echo "  --  Xcode (App Store); depois: Xcode → Settings → Components → iOS"
if [ ${#falta[@]} -gt 0 ]; then
  if [ $INSTALAR = 1 ]; then brew install "${falta[@]}"; else echo "Faltam: ${falta[*]}  (rode com --instalar)"; exit 1; fi
fi
pg_isready -q 2>/dev/null || { echo "→ iniciando o Postgres"; brew services start postgresql@15 >/dev/null; sleep 3; }

echo "→ ~/.morecheck/desenvolvimento.env"
mkdir -p "$HOME/.morecheck" && chmod 700 "$HOME/.morecheck"
ENV="$HOME/.morecheck/desenvolvimento.env"
if [ -f "$ENV" ]; then echo "  já existe (mantido)"; else
  TOK=$(openssl rand -hex 24)
  umask 077
  cat >"$ENV" <<E
# Ambiente de DESENVOLVIMENTO da nota estética (gerado por scripts/configurar_dev.sh). Não usar em produção.
DATABASE_URL=postgresql+psycopg://localhost/morecheck_dev
URL_PUBLICA=http://127.0.0.1:8000
ESTETICA_ARMAZENAMENTO=disco
ESTETICA_DIR_FOTOS=$HOME/.morecheck/fotos-dev
ESTETICA_SEGREDO_URLS=$(openssl rand -hex 32)
VISAO_WORKER_TOKENS=$TOK
MORECHECK_API_URL=http://127.0.0.1:8000
VISAO_WORKER_TOKEN=$TOK
VISAO_WORKER_ID=mac-dev
VISAO_DISPOSITIVO=cpu
CABINE_LUZ_CHAVE=$(openssl rand -hex 16)
E
  echo "  criado"
fi

echo "→ bancos"
createdb morecheck_dev 2>/dev/null && echo "  morecheck_dev criado" || echo "  morecheck_dev ok"
createdb morecheck_teste 2>/dev/null && echo "  morecheck_teste criado" || echo "  morecheck_teste ok"

echo "→ dependências"
(cd "$RAIZ/backend" && uv sync -q)
(cd "$RAIZ/visao" && uv sync -q)
(cd "$RAIZ/painel" && npm install --silent)
echo
echo "Pronto. Próximos passos:"
echo "  scripts/subir_dev.sh --rede      # backend, painel e worker acessíveis pelo iPhone"
echo "  scripts/preparar_iphone.sh       # assinatura e projeto do Xcode"
echo "  Roteiro de testes: docs/TESTE-IPHONE.md"
