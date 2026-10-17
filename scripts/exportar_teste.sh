#!/usr/bin/env bash
# Junta os resultados dos testes para mandar de volta: metadados e qualidade de cada foto, sugestões,
# logs e capturas. Com --fotos, inclui as fotos originais das últimas sessões (arquivo grande).
#   scripts/exportar_teste.sh [--fotos] [n_sessoes=5]
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
COM_FOTOS=0; N=5
for a in "$@"; do case "$a" in --fotos) COM_FOTOS=1 ;; *) N="$a" ;; esac; done
D="$(mktemp -d)/teste-iphone-$(date +%Y%m%d-%H%M)"; mkdir -p "$D"
psql -d morecheck_dev -q -A -F $'\t' -P footer=off -c "
  SELECT s.sessao_id, s.status, s.cega, s.iniciada_em, s.ultima_foto_em, s.concluida_em, s.sugestao_em,
         g.nota_final AS sugestao, g.tempo_ms
    FROM sessao_estetica s LEFT JOIN sugestao_estetica g ON g.sessao_id = s.sessao_id
   ORDER BY s.iniciada_em DESC LIMIT $N" > "$D/sessoes.tsv"
psql -d morecheck_dev -q -A -F $'\t' -P footer=off -c "
  SELECT f.sessao_id, f.passo, f.face, f.luz, f.tentativa, f.formato, f.largura, f.altura, f.tamanho_bytes,
         f.aceita, f.metadados_camera::text, f.qualidade_servidor::text, f.criada_em, f.chave
    FROM foto_estetica f
   WHERE f.sessao_id IN (SELECT sessao_id FROM sessao_estetica ORDER BY iniciada_em DESC LIMIT $N)
   ORDER BY f.criada_em" > "$D/fotos.tsv"
cp -R "$HOME/.morecheck/logs" "$D/" 2>/dev/null || true
cp -R "$HOME/.morecheck/testes" "$D/capturas" 2>/dev/null || true
if [ $COM_FOTOS = 1 ]; then
  mkdir -p "$D/fotos"
  cut -f14 "$D/fotos.tsv" | tail -n +2 | while read -r chave; do
    [ -f "$HOME/.morecheck/fotos-dev/$chave" ] && cp "$HOME/.morecheck/fotos-dev/$chave" "$D/fotos/"
  done
fi
(cd "$(dirname "$D")" && zip -qr "$HOME/Desktop/$(basename "$D").zip" "$(basename "$D")")
echo "Arquivo: ~/Desktop/$(basename "$D").zip  (anexe na issue de relato de teste no GitHub)"
