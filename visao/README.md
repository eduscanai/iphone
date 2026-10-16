# visao

Pipeline de visão da nota estética automática do Morecheck. Guia:
`docs/guia-claude-code-nota-estetica.md` (seções 8 e 15).

Hoje o pacote tem a **fase 0** (teste na mão): biblioteca de leitura, geometria e
detecção de riscos (camada (a)), mais os protótipos que respondem P1 a P6.

## Instalação

```bash
cd visao
uv sync
uv run pytest -q          # testes sintéticos: geometria, riscos, leitura
```

Python 3.12 (o backend ainda não está neste repositório; alinhar a versão quando estiver).

## Estrutura

| Caminho | O que é |
|---|---|
| `src/visao/config.py` | limiares e parâmetros; todo valor ajustável fica aqui |
| `src/visao/io_imagem.py` | HEIC, DNG e JPEG → float32, ignorando EXIF de orientação |
| `src/visao/geometria.py` | ArUco, contorno, cantos subpixel, escala, retificação, máscaras, alinhamento |
| `src/visao/riscos.py` | camada (a): top-hat, limiar por MAD, esqueleto, comprimento em mm |
| `src/visao/fase0.py` | catálogo das fotos, dimensões dos modelos, análise por face, imagens de conferência |
| `prototipos/` | scripts da fase 0 (abaixo) |
| `prototipos/fotos/` | fotos do responsável + `anotacao.csv` (fora do Git) |
| `prototipos/saida/` | tabelas, imagens e cache gerados (fora do Git) |

## Fase 0

1. `uv run python -I prototipos/gerar_marcadores.py` → `prototipos/saida/marcadores.pdf`.
2. Tirar as fotos seguindo `prototipos/PROTOCOLO.md` e copiar para `prototipos/fotos/`,
   com `anotacao.csv` (modelo em `prototipos/anotacao-modelo.csv`).
3. `uv run python -I prototipos/conferir_fotos.py`: confere nomes, fotos faltando e modelos.
4. `prototipos/rodar_tudo.sh 250` (o número é a altura da lente até a mesa, em mm).
5. Ler `docs/nota-estetica-fase0-relatorio.md`; revisar as imagens em `docs/img/fase0/`.

| Script | Responde | Saída |
|---|---|---|
| `medir_escala.py` | P2, P4: px/mm (ArUco × aparelho), altura estimada, contorno com e sem contraluz | `escala.csv`, `escala/` |
| `riscos.py` | P1, P5: riscos em `ra`, `rb` e na união | `riscos.csv`, `faces.csv`, `riscos/` |
| `comparar_iluminacao.py` | P1: só `ra` × só `rb` × nas duas, com ângulo | `iluminacao.csv` |
| `comparar_resolucao.py` | P2: riscos perdidos a 10, 15 e 20 px/mm | `resolucao.csv`, `resolucao/` |
| `profundidade_foco.py` | P3: largura de borda 10–90% e Laplaciano por pose | `foco.csv`, `foco/` |
| `cruzar_anotacao.py` | P5: técnico × algoritmo; foto suja × limpa | `cruzamento.csv`, `poeira.csv` |
| `relatorio.py` | P1–P6 + propostas D1–D4 | `docs/nota-estetica-fase0-relatorio.md` |

Para rodar com outro conjunto de fotos sem mexer nas pastas padrão:
`VISAO_FASE0_FOTOS`, `VISAO_FASE0_SAIDA` e `VISAO_FASE0_DOCS`.

### Desempenho e memória

Com fotos de 12 MP, a fase 0 inteira roda em ~30 s, com pico de ~1 GB por script.
Com 48 MP, espere ~4× (pico de ~4 GB). Num Mac de 8 GB, feche o navegador antes de rodar:
com swap, o tempo passa de segundos para dezenas de minutos.

### Limitações conhecidas

- ProRAW recente pode usar compressão que o LibRaw (`rawpy`) não lê. Se falhar, exporte em HEIF.
- HEIC: o libheif aplica as transformações do contêiner (irot/imir). Não é EXIF; nas fotos
  de uma mesma face a rotação é a mesma.
- O brilho da moldura na luz rasante vira "risco" perto da borda. Esses riscos são marcados
  `perto_borda` e ficam fora das contas principais; a fase 0 decide a faixa a excluir.
- Fotos de uma face só são realinhadas se o deslocamento passar de 2 px (guia 15.3).
