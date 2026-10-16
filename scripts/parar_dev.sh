#!/usr/bin/env bash
# Desliga o backend e o worker iniciados por scripts/subir_dev.sh.
RUN="$HOME/.morecheck/run"
matar_arvore() { local p="$1" f; for f in $(pgrep -P "$p" 2>/dev/null); do matar_arvore "$f"; done; kill "$p" 2>/dev/null || true; }
for nome in worker backend; do
  if [ -f "$RUN/$nome.pid" ]; then
    matar_arvore "$(cat "$RUN/$nome.pid")"
    rm -f "$RUN/$nome.pid"
    echo "$nome desligado"
  fi
done
