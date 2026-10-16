# Estudo de concordância — fase 1

Mede se dois técnicos dão a mesma nota usando o critério escrito. O resultado vira a linha de
base do modo automático (guia, seção 9).

## Preparar (responsável)

1. Separe **20 aparelhos**, com pelo menos 4 de cada nota (se faltar D, pelo menos 2).
2. Cole uma etiqueta **A01 a A20** em cada um (na capa da caixa ou num saquinho, nunca no aparelho).
3. Preencha `aparelhos.csv` (modelo, cor, IMEI e a nota que você espera). **Não mostre aos técnicos.**
4. Imprima ou mande para os técnicos `../nota-estetica-criterio.md`.

## Avaliar (cada técnico, sozinho)

1. Antes de olhar: tire capa e película e limpe com microfibra.
2. Avalie sob a luz normal da bancada, a ~30 cm. "Visível" = você vê a olho nu assim.
   "Só rasante" = só aparece com a lanterna deitada.
3. Dê uma nota (A, B, C ou D) para cada face e a **nota final** do aparelho.
4. Preencha **só o seu arquivo**: `tecnico1.csv` ou `tecnico2.csv` (coluna `nota`; `modelo` e `cor`
   são opcionais; use `observacao` para justificar notas difíceis).
5. Não converse sobre os aparelhos com o outro técnico até os dois terminarem.

As planilhas abrem no Excel ou no Numbers; salve de volta como CSV (UTF-8).

## Calcular

```bash
cd ~/morecheck/visao
uv run python -I ferramentas/concordancia.py ../docs/estudo/tecnico1.csv ../docs/estudo/tecnico2.csv \
  --saida ../docs/estudo/divergencias.csv
```

Meta: concordância exata ≥ 85% e kappa ponderado ≥ 0,80 na nota final. Leve `divergencias.csv` para
a reunião. Depois de aprovado, grave o kappa em `~/.morecheck/producao.env`: `ESTETICA_KAPPA_TECNICOS=<kappa>`.
