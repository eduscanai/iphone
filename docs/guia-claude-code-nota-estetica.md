# Guia de implementação para o Claude Code — Nota estética automática (Morecheck)

**Versão:** 1.1 · 2026-10-16 (contratos: seção 7.13)
**Status:** rascunho para revisão do responsável
**Base:** PRD v1.0 (`docs/prd-nota-estetica.md`) + revisão técnica de 2026-10-14
**Mudança OpenSpec:** `openspec/changes/nota-estetica-automatica/`
**Para quem:** Claude Code (ou dev) que vai construir a solução no monorepo Morecheck sem ter participado das conversas que a definiram.

> O PRD diz **o quê** e **por quê**. Este guia diz **como**, **em que ordem** e **quando parar para perguntar**.
> Onde os dois divergem, a seção 3 explica o ajuste. Um ajuste só vale depois que o responsável o aceitar (seção 0.2). Ajuste recusado = siga o PRD.

## Sumário

0. Como usar este guia
1. Missão em uma página
2. Regras de trabalho
3. Ajustes em relação ao PRD v1.0
4. Decisões pendentes
5. Arquitetura
6. Mapa de pastas e arquivos
7. Contratos (fonte da verdade)
8. Fase 0 — Teste na mão
9. Fase 1 — Critério de nota
10. Fase 2 — Cabine A
11. Fase 3 — Backend, painel e laudo
12. Fase 4 — Nota sugerida
13. Fase 5 — Modo automático
14. Referência: câmera iOS
15. Referência: pipeline de visão
16. Referência: motor de critério
17. Testes e verificação
18. Licenças, bases e modelos
19. Riscos conhecidos
- Apêndice A — Dimensões e zonas por modelo
- Apêndice B — Prompts prontos para cada sessão
- Apêndice C — Glossário

---

## 0. Como usar este guia

### 0.1 Para o responsável (humano)

1. Coloque este arquivo em `docs/guia-claude-code-nota-estetica.md` e o PRD em `docs/prd-nota-estetica.md`. Se estiverem em outro lugar, ajuste os caminhos citados aqui.
2. Acrescente ao `CLAUDE.md` da raiz do repositório:

   ```markdown
   ## Nota estética automática
   - Guia: docs/guia-claude-code-nota-estetica.md — leia as seções 0 a 7 antes de qualquer tarefa desta feature.
   - PRD: docs/prd-nota-estetica.md · OpenSpec: openspec/changes/nota-estetica-automatica/
   - Uma fase por vez. Nos pontos marcados PARADA, pare e peça ação ou decisão do responsável.
   ```

3. Trabalhe **uma fase por sessão** do Claude Code (nas fases 2 a 4, uma sessão por componente). Os prompts prontos estão no Apêndice B.
4. A sua parte: tudo que é físico (fotos, montagem, gravar o ESP32, instalar o app no iPhone), as decisões da seção 4 e aprovar commits.

### 0.2 Para o Claude Code

- **Início de toda sessão:** leia nesta ordem:
  1. seções 0 a 7 deste guia;
  2. a seção da fase atual;
  3. as referências técnicas (seções 14 a 18) que a fase indicar;
  4. `openspec/changes/nota-estetica-automatica/design.md` e `tasks.md`;
  5. os arquivos vizinhos do componente que você vai mexer.
- **Primeira sessão do projeto:** apresente ao responsável a tabela da seção 3 e a lista da seção 4. Registre o que ele aceitar ou recusar em `design.md`, numa seção "Decisões", com data.
- **Marcadores usados neste guia:**
  - **PARADA** — pare, mostre o que tem e espere ação ou decisão humana.
  - **VERIFICAR** — fato que pode ter mudado (API de biblioteca, especificação de aparelho, licença). Confira antes de usar.
  - **PADRÃO** — o que fazer se o responsável não puder responder agora.
- **Fim de toda sessão:** escreva um resumo curto com o que foi feito, como verificar, o que ficou pendente e quais decisões são necessárias. Atualize `tasks.md`.

---

## 1. Missão em uma página

Dar a cada iPhone usado uma **nota estética A/B/C/D objetiva, repetível e auditável**, com fotos e defeitos medidos em mm no laudo. Volume: ~4.000 aparelhos/mês (~200/dia). A nota define o preço e o canal de venda (venda direta, reparo/polimento, peças).

**Como funciona (cabine A):**

1. O aparelho avaliado termina os testes funcionais e mostra o **QR da sessão**.
2. O técnico o coloca no **berço**. Um **iPhone da empresa**, fixo olhando para baixo em **modo Cabine**, lê o QR, descobre o modelo e pede ao aparelho avaliado para **apagar a tela**.
3. Para cada face, a cabine tira fotos com **luz ambiente** e com **luz rasante**. Ela controla as luzes por um **ESP32** e dispara sozinha quando a imagem fica parada e nítida.
4. As fotos sobem para o **backend**. Um **worker de visão** retifica as imagens usando o próprio aparelho como régua, detecta riscos, trincas, amassados e lascados e mede cada defeito em mm.
5. O backend aplica o **critério de nota** (regras versionadas) e gera a **nota sugerida**.
6. O técnico **confirma ou corrige** no **painel**. Cada correção vira dado de treino.
7. A nota final entra no **laudo** com fotos, defeitos e origem (`tecnico`, `sugerida` ou `automatica`).
8. Quando a máquina concordar com os técnicos o suficiente (seção 13), a nota passa a ser **automática**.

**Metas:** cabine ≤ 60 s por aparelho; sugestão ≤ 10 s após a última foto; app iOS só com API pública.

**Fora do escopo:** robô/esteira (fase 2B, OpenScan), Android, iPad, Apple Watch, tela ligada (pixel morto já é teste funcional), polimento e reparo.

---

## 2. Regras de trabalho

Valem em todas as fases. Se conflitarem com qualquer outra instrução deste guia, estas vencem.

1. **Leia antes de escrever.** Antes de criar um arquivo, leia os vizinhos e siga o estilo: nomes em pt-BR, estrutura, padrões de autenticação, log, auditoria e testes que o componente já usa.
2. **pt-BR em tudo:** nomes no código, comentários, mensagens, documentos e mensagens de commit.
3. **Não commitar sem pedido.** Nunca faça push, rode migração em produção, apague dados ou mexa em servidor sem pedido explícito.
4. **Segredos só em `~/.morecheck/producao.env`** (ou no arquivo de desenvolvimento que o projeto já usar). Nunca em código, testes, logs, commits ou mensagens. Nunca imprima o valor de um segredo.
5. **App iOS só com API pública** (meta: App Store, não listado). Nada de API privada, nem provisoriamente.
6. **Python com `uv`.** Cada pacote declara as dependências no próprio `pyproject.toml`, com `uv.lock` versionado. Rode scripts com `uv run python -I` (como pede o PRD).
7. **Licenças:** não use base ou modelo com licença não comercial. Não adicione dependência AGPL ou GPL ao produto sem aprovação (decisão D7). Registre toda base em `visao/DATASETS.md` e todo modelo treinado em `visao/MODELOS.md`.
8. **Divergiu do PRD ou deste guia?** Registre em `design.md` (motivo, alternativa, impacto) e avise no resumo da sessão.
9. **Físico é com o humano.** Para fotos, montagem, gravação de firmware ou instalação no iPhone, pare (PARADA) e dê instruções passo a passo, com o resultado esperado de cada passo.
10. **Simples primeiro:** OpenCV antes de deep learning; long-poll antes de WebSocket, se o backend ainda não tiver WebSocket; tabela no Postgres antes de Redis.
11. **Reprodutível:** sementes fixas, versões fixadas, modelos com versão e hash. Mesma foto e mesmo modelo → mesma saída.
12. **Evidência visual:** todo algoritmo de visão gera imagens anotadas para conferência humana. Número sem imagem não convence a bancada.
13. **Definição de pronto de qualquer tarefa:** testes passando, lint do componente limpo, documentação e `tasks.md` atualizados, nenhum segredo exposto, nenhum TODO sem dono.

---

## 3. Ajustes em relação ao PRD v1.0

Saíram da revisão técnica de 2026-10-14. Todos estão **propostos**: apresente-os na primeira sessão e registre a decisão. Os que dependem de medição são confirmados na fase indicada.

| # | Tema | PRD v1.0 | Este guia | Por quê | Validação |
|---|---|---|---|---|---|
| R1 | Luz rasante | 1 barra, paralela ao lado comprido | 2 barras a 90° (canais `a` e `b`), fotos `rasante_a` e `rasante_b`, ou `rasante_ab` se as duas juntas bastarem | Risco paralelo à luz quase não espalha luz e some na foto | Fase 0 (D1) |
| R2 | Foco | travado num valor único | `lensPosition` calibrado **por pose** | As faces ficam em alturas diferentes; a profundidade de campo a 25–30 cm é de ±1–2 cm | Fase 0 |
| R3 | Laterais, topo e base | aparelho em pé na canaleta de 10 mm | testar **espelhos a 45°** com o aparelho sempre deitado (2 poses no total) contra suportes em pé | Em pé, a face fica a ~72 mm (lateral) ou ~147 mm (ponta) acima do berço: perto ou abaixo da distância mínima de foco, e instável | Fase 0/2 (D3) |
| R4 | Resolução de análise | retificar a 10 px/mm | detectar na resolução nativa; retificar a ≥ px/mm nativo (alvo ≥ 20) | 10 px/mm apaga microrriscos | Fase 0 |
| R5 | Altura da câmera | 30–35 cm | escolher pelo px/mm alvo: com 48 MP, ~25 cm dá ~22 px/mm e 35 cm dá ~16 px/mm | Resolução no plano do aparelho | Fase 0 (D2) |
| R6 | Película, capa e sujeira | detector de película é item futuro | retirar película e capa e **limpar com microfibra** antes da cabine (processo obrigatório) | Película riscada parece tela riscada; poeira parece microrrisco | Processo |
| R7 | PatchCore | por cor e por modelo | por **família de acabamento**, só traseira e moldura, em blocos (tiles) | Cor × modelo × face exigiria dezenas de milhares de fotos nota A | Fase 4 |
| R8 | Amassado "≤ 3 mm" | medida não definida | **diâmetro aparente** na foto rasante | Profundidade não se mede com uma câmera de cima | Fase 1 |
| R9 | "Visível" | aparece na foto de luz ambiente | visível a olho nu a ~30 cm na luz da bancada; o algoritmo é calibrado contra isso | Senão a regra depende do limiar do próprio algoritmo | Fase 1 |
| R10 | Meta do automático | ≥ 90% exato e 0 casos a 2 notas em 200 | + kappa ponderado ≥ linha de base técnico × técnico; recall ≥ 80% em cada nota; medido só em amostra cega | A meta de 90% pode superar a concordância entre humanos (85%); acurácia engana se quase tudo for B | Fase 5 |
| R11 | Amostra cega | — | parte das sessões não mostra a sugestão ao técnico antes de ele dar a nota | Quem vê a sugestão tende a confirmá-la (viés de automação) e isso infla a concordância | Fase 3 |
| R12 | Armazenamento | disco da VPS, ~100 GB/mês | object storage S3-compatível (R2 ou S3); prever de ~0,15 TB/mês (roteiro com espelhos, 6 fotos) a ~0,5 TB/mês (roteiro em pé, 13 a 18 fotos) | Foto de 48 MP tem 4–15 MB | Fase 0 mede (D8) |
| R13 | Quem calcula a nota | serviço de visão | a visão devolve **defeitos**; o **backend** aplica o critério (motor versionado) | Recalcular na hora quando o técnico marca ou desmarca um defeito; uma só versão do critério | — |
| R14 | Fila | "fila de tarefas" | tabela no Postgres + worker que **puxa** tarefas por HTTPS | O worker pode rodar num Mac da loja atrás de NAT; sem Redis | — |
| R15 | Detector de defeitos | YOLO11 (Ultralytics) | **RF-DETR** (Apache-2.0) por padrão; Ultralytics só com licença Enterprise | Ultralytics é AGPL-3.0 ou licença comercial paga (seção 18) | D7 |
| R16 | Achar o aparelho na foto | YOLO11-seg pré-treinado no COCO | contorno por OpenCV, com foto de contraluz se adotada (D4); RF-DETR-Seg como plano B | iPhone preto em fundo preto tem pouco contraste; YOLO não reconhece uma lateral de 7 mm | Fase 0 |
| R17 | Exposição | travada | travada com tempo múltiplo de 1/120 s (ex.: 1/60 s) | Rede de 60 Hz: lâmpadas oscilam a 120 Hz e criam faixas na foto | Fase 2 |
| R18 | Tela preta | preto puro | preto + brilho 0, restaurado depois | Em LCD (SE 2ª/3ª, XR, 11) preto não é preto | Fase 2 |
| R19 | Envio das fotos | fila local | foto a foto, durante a captura, com `Idempotency-Key` | Ganha tempo e evita duplicata em reenvio | — |
| R20 | Processamento | depois da última foto | uma tarefa por foto à medida que chegam + fusão no final | Cumprir ≤ 10 s após a última foto | — |
| R21 | Orientação da imagem | — | rotação fixa no app (`videoRotationAngle = 0`) e **EXIF ignorado** no Python | Câmera apontada para baixo tem orientação instável | — |
| R22 | Tipo `anomalia` | — | região anômala sem classe (vinda do PatchCore) vira defeito `anomalia`, sempre revisado pelo técnico | O PatchCore aponta onde, mas não diz o quê | Fase 1/4 |

---

## 4. Decisões pendentes

Decisões do responsável. O **PADRÃO** vale enquanto não houver resposta (por exemplo, numa sessão sem supervisão).

| # | Decisão | Quando | PADRÃO |
|---|---|---|---|
| D1 | Uma ou duas direções de luz rasante; fotos separadas ou juntas | fim da fase 0 | duas barras, fotos separadas |
| D2 | Altura da câmera e px/mm alvo | fim da fase 0 | a altura que dá ≥ 20 px/mm no plano do aparelho, respeitando o foco mínimo |
| D3 | Como fotografar laterais, topo e base: espelhos a 45° ou suportes em pé com presets de foco | fase 0/2 | espelhos, se as bordas refletidas saírem nítidas e bem iluminadas na fase 0 (`espelho_amb`, `espelho_ra`); senão, suportes em pé |
| D4 | Usar foto de contraluz para achar o contorno | fim da fase 0 | sim, se o contorno sem ela falhar em > 2% das fotos |
| D5 | Lacunas do critério (seção 16.4) | fase 1 | marcar "a definir" e nunca automatizar essas faixas |
| D6 | Onde roda o worker de visão (VPS, Mac M-series da loja, GPU na nuvem) | início da fase 4 | Mac da loja para treino; VPS (CPU) para a camada OpenCV |
| D7 | Detector: RF-DETR (Apache-2.0) ou Ultralytics com licença Enterprise | início da fase 4 | RF-DETR |
| D8 | Armazenamento: R2/S3 ou disco da VPS | início da fase 3 | R2; disco só em desenvolvimento |
| D9 | Técnico confirma a nota só no painel ou também na tela da cabine | fase 2/3 | só no painel (como no PRD); a cabine mostra um resumo |
| D10 | Autenticar a cabine por pareamento (token de cabine) | fase 3 | sim |
| D11 | O que aparece na página pública de verificação (QR do laudo) | fase 3 | miniaturas das faces na luz ambiente + lista de defeitos; sem fotos originais |
| D12 | Percentual da amostra cega | fase 3 | 100% nas 2 primeiras semanas de uso; depois 10% |

---

## 5. Arquitetura

```
                          ┌─────────────────────────────────┐
                          │ Aparelho avaliado               │
                          │ app de testes (ou página)       │
                          │ mostra QR · obedece "tela"      │
                          └───────────────┬─────────────────┘
                                          │ GET /pagina/{token}/eventos (long-poll)
 ┌────────────────────────┐   HTTPS       ▼
 │ iPhone câmera          ├──────►┌───────────────────────────────┐  HTTPS (worker puxa)  ┌──────────────────────┐
 │ app em modo Cabine     │       │ Backend FastAPI + Postgres    │◄──────────────────────┤ Worker de visão      │
 │ câmera travada         │       │ rotas cabine/painel/visão     │  fotos por URL        │ visao/ (Python, uv)  │
 │ roteiro de faces       │       │ motor de critério (nota)      │  assinada             │ OpenCV · PatchCore   │
 │ fila local de envio    │       │ fila: tarefa_visao            ├──────────────────────►│ RF-DETR              │
 └──────────┬─────────────┘       │ eventos: evento_sessao        │                       └──────────────────────┘
            │ HTTP local (mDNS)   └───────┬──────────────┬────────┘
            ▼                             │              │
 ┌────────────────────────┐               ▼              ▼
 │ ESP32 cabine-luz       │        Object storage   Painel React (avaliação, concordância)
 │ canais a, b, difusa,   │        (R2/S3)          Laudo PDF + página de verificação
 │ contraluz              │
 └────────────────────────┘
```

### 5.1 Responsabilidades

| Componente | Faz | Não faz |
|---|---|---|
| App modo Cabine (`app-ios/Sources/Cabine/`) | lê QR, controla câmera e luzes, roteiro, controle de qualidade local, envio | calcular nota |
| Tela QR + preto (aparelho avaliado) | mostra QR, apaga a tela sob comando | — |
| ESP32 (`hardware/cabine-luz/`) | liga e desliga canais de luz e confirma o estado | lógica de roteiro |
| Backend (`backend/app/estetica/`) | sessões da cabine, fotos, fila, eventos, **critério de nota**, avaliações, concordância, gate do automático | processar imagem |
| Worker (`visao/`) | qualidade, geometria, retificação, detecção, medição, zonas, fusão | decidir a nota |
| Painel (`painel/src/estetica/`) | fila de avaliação, confirmação e correção, relatório de concordância | — |
| Laudo (`backend/app/laudo/`) | bloco "Estado estético" | — |

### 5.2 Sequência de uma avaliação

1. A cabine lê o QR → `GET /cabine/{token}` → recebe modelo, dimensões e roteiro.
2. A cabine chama `POST /cabine/{token}/tela {"acao": "preto"}` → o backend grava um `evento_sessao` → o aparelho avaliado o recebe no long-poll e fica preto com brilho 0. A cabine confirma vendo a região do aparelho escurecer na imagem.
3. Para cada passo do roteiro: o técnico posiciona → a cabine espera estabilidade → para cada luz: `POST http://<esp32>/luz`, espera a confirmação, captura, faz o controle de qualidade local e enfileira `POST /cabine/{token}/fotos` (envio em segundo plano).
4. Backend: guarda a foto no storage e cria `tarefa_visao` do tipo `foto`.
5. Worker: reserva a tarefa → baixa a foto → qualidade, geometria e detecções → `POST /visao/tarefas/{id}/resultado`.
6. A cabine chama `POST /cabine/{token}/concluir` → o backend cria a tarefa `fusao`, liberada quando todas as tarefas `foto` da sessão terminarem.
7. Worker: fusão por face → defeitos finais → backend aplica o critério → grava `sugestao_estetica` → evento `sugestao_pronta`.
8. Painel: o técnico abre a sessão (a sugestão fica escondida se a sessão for cega) → confirma ou corrige → `POST /registros/{id}/estetica`.
9. Laudo: bloco "Estado estético" com nota, miniaturas e defeitos.

---

## 6. Mapa de pastas e arquivos

Arquivos novos (★) e pontos de integração. Siga a estrutura real do repositório se ela divergir deste mapa.

```
visao/                                   ★ pacote Python novo (uv, layout src/)
├── pyproject.toml · uv.lock · README.md
├── DATASETS.md                          bases usadas: licença, atribuição, data, URL
├── MODELOS.md                           modelos treinados: versão, hash, dados, métricas
├── prototipos/                          fase 0
│   ├── fotos/                           fotos do humano (no .gitignore)
│   ├── saida/                           imagens e tabelas geradas (no .gitignore)
│   ├── gerar_marcadores.py
│   ├── medir_escala.py
│   ├── riscos.py
│   ├── comparar_iluminacao.py
│   ├── comparar_resolucao.py
│   ├── profundidade_foco.py
│   └── relatorio.py
├── src/visao/
│   ├── config.py
│   ├── io_imagem.py                     HEIC/JPEG/DNG → numpy, ignorando EXIF
│   ├── qualidade.py
│   ├── geometria.py                     contorno, retas das bordas, cantos, mm/px
│   ├── retificacao.py                   homografia → imagem no referencial da face
│   ├── zonas.py                         máscaras a partir de zonas em mm
│   ├── riscos.py                        camada (a)
│   ├── anomalia.py                      camada (b) PatchCore
│   ├── detector.py                      camada (c) RF-DETR
│   ├── fusao.py                         junta detecções da mesma face em várias fotos
│   ├── anotar.py
│   ├── pipeline.py                      processar_foto(), fundir_sessao()
│   ├── cliente_api.py                   reservar, renovar, resultado, falha
│   └── worker.py                        loop principal (com modo --nulo)
├── ferramentas/
│   ├── concordancia.py                  técnico × técnico e máquina × técnico
│   ├── sintetico.py                     imagens sintéticas para testes
│   ├── simular_cabine.py                teste ponta a ponta pela API
│   ├── marcar_zonas.py                  ferramenta do humano para medir zonas
│   ├── baixar_bases.py                  Roboflow → dados/
│   ├── exportar_dataset.py              marcações do painel → COCO
│   ├── treinar_detector.py
│   └── treinar_patchcore.py
└── tests/

backend/app/estetica/                    ★ módulo novo
├── enums.py · esquemas.py · modelos.py
├── dimensoes.py                         Apêndice A
├── criterio.py                          motor (seção 16)
├── criterios/criterio-v1.yaml
├── armazenamento.py                     disco ou s3
├── fila.py                              tarefa_visao (SKIP LOCKED)
├── eventos.py                           evento_sessao + long-poll
├── concordancia.py · gate.py
├── rotas_cabine.py · rotas_pagina.py · rotas_painel.py · rotas_visao.py
└── retencao.py
backend/alembic/versions/<rev>_estetica.py   ★
backend/tests/estetica/                      ★
backend/app/laudo/…                          integração: bloco "Estado estético"

app-ios/Sources/Cabine/                  ★ modo Cabine (iPhone câmera)
├── CabineView.swift · CabineModelo.swift    máquina de estados do roteiro
├── CameraCabine.swift                       AVFoundation
├── Calibracao.swift · PerfilCamera.swift
├── DetectorEstabilidade.swift · QualidadeLocal.swift
├── LuzCabine.swift                          cliente HTTP do ESP32
├── EnvioFotos.swift                         fila local (padrão de Envio.swift)
├── Pareamento.swift
└── Voz.swift                                opcional
app-ios/Sources/Estetica/TelaQRPreto.swift   ★ no aparelho avaliado
pagina-testes/src/…/TelaQRPreto.svelte       ★ alternativa web (seção 10.4)

painel/src/estetica/                     ★ seguir a estrutura e a extensão (.jsx ou .tsx) do painel
├── FilaAvaliacao · TelaAvaliacao · VisualizadorFace
├── ListaDefeitos · SeletorNota
└── RelatorioConcordancia

hardware/cabine-a/                       ★ montagem física
├── README.md                            compras, montagem, alturas, conferências
├── berco.scad                           berço paramétrico (OpenSCAD) → STL
└── marcadores-aruco.pdf
hardware/cabine-luz/                     ★ firmware ESP32 (PlatformIO)
├── platformio.ini · src/main.cpp
├── include/segredos.exemplo.h           include/segredos.h fica no .gitignore
└── README.md                            ligação elétrica

docs/
├── nota-estetica-criterio.md            ★ fase 1
├── nota-estetica-fase0-relatorio.md     ★ fase 0
└── estudo-concordancia-v1.csv           ★ fase 1 (modelo de planilha)
```

---

## 7. Contratos (fonte da verdade)

Qualquer mudança aqui exige atualizar este guia, `design.md` e os dois lados do contrato no mesmo trabalho.

### 7.1 Enumerações

| Nome | Valores |
|---|---|
| `Face` | `frente`, `traseira`, `lat_esq` (lado dos botões de volume), `lat_dir` (lado do botão lateral), `topo`, `base` (lado do conector) |
| `Luz` | `ambiente`, `rasante_a` (barra paralela ao lado comprido do berço), `rasante_b` (barra paralela ao lado curto), `rasante_ab` (as duas), `contraluz` |
| `Pose` | `deitado`, `lateral`, `ponta` (se D3 = suportes em pé) |
| `Lado` | `tela_cima`, `tela_baixo` (para a pose `deitado`) |
| `TipoDefeito` | `risco`, `trinca`, `lascado`, `amassado`, `descascado`, `desgaste`, `mancha`, `anomalia` |
| `Zona` | `tela`, `recorte_tela` (notch ou Dynamic Island), `vidro_traseiro`, `ilha_camera`, `lente_camera`, `moldura`, `quina`, `botao`, `porta` |
| `Visibilidade` | `visivel`, `so_rasante` |
| `OrigemDefeito` | `maquina`, `tecnico` |
| `EstadoDefeito` | `proposto`, `confirmado`, `rejeitado` |
| `OrigemNota` | `tecnico` (técnico deu ou alterou), `sugerida` (técnico aceitou a sugestão sem mudar), `automatica` (sem humano) |
| `Nota` | `A`, `B`, `C`, `D` (A melhor) |
| `ModoEstetica` (por loja) | `desligado`, `assistido`, `automatico` |
| `StatusSessaoEstetica` | `capturando`, `processando`, `aguardando_tecnico`, `avaliada`, `erro` |
| `TipoTarefa` / `StatusTarefa` | `foto`, `fusao` / `pendente`, `reservada`, `concluida`, `falhou` |

### 7.2 Referencial das faces (mm)

Toda medida e toda zona é dada em mm no referencial da face, **como vista de fora**. A imagem retificada da face tem `W × R` por `H × R` pixels, com `R` = px/mm de retificação (configurável; alvo ≥ 20).

Coordenadas do aparelho: +X = lado do botão lateral (direita de quem olha a tela), +Y = topo, +Z = normal da tela.

| Face | W × H | x vai de → até | y vai de → até | Observação |
|---|---|---|---|---|
| `frente` | largura × altura | `lat_esq` → `lat_dir` | topo → base | origem no canto topo/lado do volume |
| `traseira` | largura × altura | `lat_dir` → `lat_esq` | topo → base | a ilha de câmeras fica perto da origem |
| `lat_esq` | espessura × altura | traseira → tela | topo → base | |
| `lat_dir` | espessura × altura | tela → traseira | topo → base | |
| `topo` | largura × espessura | `lat_dir` → `lat_esq` | tela → traseira | vista de fora, tela para cima na imagem |
| `base` | largura × espessura | `lat_esq` → `lat_dir` | tela → traseira | vista de fora, tela para cima na imagem |

`caixa_mm` = `[x, y, w, h]` nesse referencial. `geometria_mm` = `{"tipo": "polilinha" ou "poligono", "pontos": [[x, y], …]}`.

### 7.3 API da cabine (app modo Cabine)

Autenticação: `Authorization: Bearer <token_cabine>` (pareamento, D10) + `{token}` = token da sessão lido no QR. Siga o padrão de erros do backend.

**`GET /cabine/{token}`** — abre a sessão para captura. Cria `sessao_estetica` (e sorteia `cega`) se ainda não existir.

```json
{
  "sessao_id": "8f1c…",
  "aparelho": {
    "identificador": "iPhone14,5",
    "nome": "iPhone 13",
    "cor": "meia-noite",
    "tela": "oled",
    "dimensoes_mm": {"largura": 71.5, "altura": 146.7, "espessura": 7.65}
  },
  "roteiro": {
    "versao": "roteiro-v1",
    "passos": [
      {"ordem": 1, "pose": "deitado", "lado": "tela_cima",  "faces": ["frente", "lat_esq", "lat_dir", "topo", "base"],
       "luzes": ["ambiente", "rasante_a", "rasante_b"], "instrucao": "Tela para cima, topo encostado no batente."},
      {"ordem": 2, "pose": "deitado", "lado": "tela_baixo", "faces": ["traseira", "lat_esq", "lat_dir", "topo", "base"],
       "luzes": ["ambiente", "rasante_a", "rasante_b"], "instrucao": "Vire: traseira para cima."}
    ]
  },
  "mostrar_sugestao": true
}
```

O exemplo é o roteiro com espelhos (D3). Com suportes em pé, cada lateral, o topo e a base viram passos próprios com `pose` `lateral` ou `ponta` e `faces` com um item só. **O roteiro vem do backend**, então mudar o roteiro não exige nova versão do app.

Erros: `404` sessão inexistente ou expirada; `409` sessão já avaliada (aceitar `?refazer=1`); `422` modelo sem dimensões cadastradas, com mensagem clara (ex.: "Modelo iPhone14,5 sem dimensões cadastradas").

**`POST /cabine/{token}/fotos`** — `multipart/form-data`, cabeçalho `Idempotency-Key: <uuid gerado no iPhone por foto>`.

| Campo | Tipo | Exemplo |
|---|---|---|
| `passo` | int | `1` |
| `face` | `Face` (principal do passo) | `frente` |
| `luz` | `Luz` | `rasante_a` |
| `pose`, `lado` | `Pose`, `Lado` | `deitado`, `tela_cima` |
| `tentativa` | int | `1` |
| `metadados` | JSON (texto) | ver abaixo |
| `arquivo` | HEIC, JPEG ou DNG, ≤ 40 MB | — |

```json
{
  "camera": {"modelo": "iPhone15,3", "lente": "grande_angular_1x", "app_versao": "1.8.0"},
  "exposicao": {"duracao_s": 0.016667, "iso": 125.0},
  "foco": {"lens_position": 0.62},
  "balanco_branco": {"r": 1.92, "g": 1.0, "b": 1.71},
  "dimensoes_px": {"largura": 8064, "altura": 6048},
  "formato": "heic",
  "rotacao_graus": 0,
  "perfil_calibracao_versao": 3,
  "capturada_em": "2026-10-20T14:03:11.402-03:00",
  "qualidade_local": {"nitidez": 812.4, "estouro_pct": 0.02, "contorno_ok": true}
}
```

Resposta `201`: `{"foto_id": "…", "duplicada": false}`. A mesma `Idempotency-Key` devolve a mesma foto com `"duplicada": true`. Ao receber, o backend grava no storage, cria `foto_estetica` e cria `tarefa_visao(tipo=foto)`.

**`POST /cabine/{token}/concluir`** — corpo `{"fotos_enviadas": 6}`. Resposta `202` `{"status": "processando"}`. Responde `409` com a lista do que falta se faltar foto exigida pelo roteiro. Cria a tarefa `fusao`.

**`POST /cabine/{token}/tela`** — corpo `{"acao": "preto"}` (ou `"qr"`, `"normal"`). Resposta `202`. Grava `evento_sessao(tipo=tela)`.

**`GET /cabine/{token}/sugestao`** — a cabine consulta a cada 1 s (ou long-poll).

```json
{
  "status": "pronta",
  "mostrar": true,
  "nota_final": "B",
  "notas_por_face": {"frente": "B", "traseira": "A", "lat_esq": "A", "lat_dir": "A", "topo": "A", "base": "A"},
  "resumo": ["Tela: 3 riscos só rasante (maior 9,8 mm) → B"],
  "refazer": []
}
```

`status` ∈ `pendente`, `processando`, `pronta`, `erro`. Se a sessão for cega: `{"status": "pronta", "mostrar": false}`. `refazer` lista faces cujas fotos o worker reprovou.

**Pareamento da cabine (D10):** `POST /cabines/pareamento` (painel, administrador da loja) → `{"codigo": "K7PQ-3XWD", "expira_em": "…"}`, exibido como QR no painel. `POST /cabines/ativar` (app) com `{"codigo": "…", "nome": "Cabine 1"}` → `{"cabine_id": "…", "token": "…"}`. O token vai para o Keychain e o backend guarda só o hash. A revogação é feita no painel.

### 7.4 API do aparelho avaliado

**`GET /pagina/{token}/eventos?apos={seq}`** — long-poll de até 25 s. Responde assim que houver evento novo ou com lista vazia no tempo-limite.

```json
{"eventos": [{"seq": 12, "tipo": "tela", "dados": {"acao": "preto"}}]}
```

Se o backend já tiver WebSocket por sessão, use-o com o mesmo formato de evento.

### 7.5 API do painel

Autenticação e escopo por loja: padrão do backend.

| Método e rota | Uso |
|---|---|
| `GET /estetica/fila?status=aguardando_tecnico` | sessões esperando avaliação (modelo, hora, status da sugestão, `cega`) |
| `GET /estetica/sessoes/{sessao_id}` | fotos por face (URLs assinadas: retificada, anotada, original), defeitos, zonas do modelo, sugestão (omitida se cega e ainda sem avaliação final) |
| `POST /estetica/criterio/avaliar` | corpo: lista de defeitos → notas por face, nota final, justificativas, margens (função pura; o painel chama enquanto o técnico edita) |
| `POST /registros/{id}/estetica` | grava a avaliação final (corpo abaixo); correção = novo POST com `substitui_id` |
| `GET /estetica/concordancia?de=&ate=&loja=&modelo=&face=&tecnico=&incluir_nao_cegas=false` | métricas da seção 13 |
| `GET /estetica/config` · `PUT /estetica/config` | modo e percentual cego da loja; `PUT` com `modo=automatico` responde `409` se o gate não passar (RF11) |

Corpo de `POST /registros/{id}/estetica`:

```json
{
  "sessao_id": "8f1c…",
  "notas_por_face": {"frente": "B", "traseira": "A", "lat_esq": "A", "lat_dir": "A", "topo": "A", "base": "A"},
  "nota_final": "B",
  "defeitos": [
    {"proposta_id": "d1…", "estado": "confirmado"},
    {"proposta_id": "d2…", "estado": "rejeitado"},
    {"proposta_id": "d3…", "estado": "confirmado", "tipo": "trinca"},
    {"novo": {"face": "frente", "tipo": "risco", "zona": "tela", "visibilidade": "so_rasante",
              "caixa_mm": [12.0, 40.5, 6.2, 1.1], "foto_id": "f9…"}}
  ],
  "justificativa": null,
  "substitui_id": null
}
```

Regras do backend: recalcula `nota_regra` com os defeitos confirmados e novos; exige `justificativa` se `nota_final` ≠ `nota_regra`; define `origem` (`sugerida` se tudo igual à sugestão, senão `tecnico`); grava `cega` a partir da sessão; tudo vai para a auditoria.

### 7.6 API do worker de visão

Autenticação: `Authorization: Bearer <VISAO_WORKER_TOKEN>`.

| Método e rota | Uso |
|---|---|
| `POST /visao/tarefas/reservar` | corpo `{"worker_id": "mac-loja-1", "tipos": ["foto", "fusao"]}` → `200` com a tarefa ou `204` sem tarefa |
| `POST /visao/tarefas/{id}/renovar` | estende o prazo de reserva (lease) |
| `POST /visao/tarefas/{id}/resultado` | resultado (7.9) |
| `POST /visao/tarefas/{id}/falha` | `{"erro": "…", "recuperavel": true}`; recuperável volta para a fila até 3 tentativas |

Tarefa `foto` entregue ao worker (valores ilustrativos):

```json
{
  "tarefa_id": "t1…", "tipo": "foto", "sessao_id": "8f1c…", "lease_ate": "…",
  "foto": {"foto_id": "f1…", "passo": 1, "face": "frente", "faces": ["frente", "lat_esq", "lat_dir", "topo", "base"],
           "luz": "rasante_a", "pose": "deitado", "lado": "tela_cima",
           "url": "https://…assinada…", "formato": "heic", "metadados": {}},
  "fotos_irmas": [{"foto_id": "f0…", "luz": "ambiente", "url": "https://…"}],
  "aparelho": {"identificador": "iPhone14,5", "dimensoes_mm": {}, "raio_canto_mm": 9.0,
               "zonas_mm": {"frente": {"recorte_tela": [[25.4, 1.5, 20.0, 4.0]]}},
               "familia": {"traseira": "vidro_brilhante_escuro", "moldura": "aluminio_escuro"}},
  "perfil_calibracao": {},
  "config": {"px_por_mm_retificacao": 20, "versao_pipeline_minima": "0.3.0"},
  "upload": {"retificada": "https://…put…", "anotada": "https://…put…"}
}
```

`fotos_irmas` são as outras fotos do mesmo passo (por exemplo, a de luz ambiente para a subtração). A tarefa `foto` de uma luz rasante só é liberada depois que a foto `ambiente` do mesmo passo chegou.

### 7.7 Eventos

Tabela `evento_sessao` + long-poll (consulta a cada 500 ms, até 25 s). Tipos:

| Tipo | Para | Dados |
|---|---|---|
| `tela` | aparelho avaliado | `{"acao": "preto"}` (ou `qr`, `normal`) |
| `sugestao_pronta` | cabine, painel | `{"sugestao_id": "…"}` |
| `foto_reprovada` | cabine | `{"foto_id": "…", "face": "lat_esq", "motivo": "contorno não encontrado"}` |

### 7.8 Tabelas (migração Alembic)

Adapte os tipos das chaves estrangeiras (`sessao`, `loja`, `usuario`, `registro`) ao esquema existente. Enums como `text` com `CHECK`, ou ENUM nativo se esse for o padrão do backend.

```sql
CREATE TABLE cabine (
  id           uuid PRIMARY KEY,
  loja_id      <FK loja> NOT NULL,
  nome         text NOT NULL,
  token_hash   text NOT NULL,
  ativa        boolean NOT NULL DEFAULT true,
  criada_em    timestamptz NOT NULL DEFAULT now(),
  revogada_em  timestamptz
);

CREATE TABLE sessao_estetica (
  sessao_id       <FK sessao> PRIMARY KEY,
  cabine_id       uuid REFERENCES cabine(id),
  status          text NOT NULL,          -- StatusSessaoEstetica
  cega            boolean NOT NULL,
  roteiro_versao  text NOT NULL,
  iniciada_em     timestamptz NOT NULL DEFAULT now(),
  ultima_foto_em  timestamptz,
  concluida_em    timestamptz,            -- POST /concluir
  sugestao_em     timestamptz,
  avaliada_em     timestamptz
);

CREATE TABLE foto_estetica (
  id                  uuid PRIMARY KEY,
  sessao_id           <FK sessao> NOT NULL,
  passo               int NOT NULL,
  face                text NOT NULL,      -- face principal do passo
  luz                 text NOT NULL,
  pose                text NOT NULL,
  lado                text,
  tentativa           int NOT NULL DEFAULT 1,
  chave               text NOT NULL,      -- chave no storage
  formato             text NOT NULL,      -- heic, jpeg ou dng
  largura             int NOT NULL,
  altura              int NOT NULL,
  tamanho_bytes       bigint NOT NULL,
  sha256              text NOT NULL,
  metadados_camera    jsonb NOT NULL,
  qualidade_local     jsonb,
  qualidade_servidor  jsonb,
  aceita              boolean,            -- null até o worker avaliar
  geometria           jsonb,              -- por face extraída: cantos, homografia, mm/px
  chave_retificada    text,
  chave_anotada       text,
  idempotency_key     text NOT NULL UNIQUE,
  criada_em           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON foto_estetica (sessao_id, passo, luz);

CREATE TABLE tarefa_visao (
  id             uuid PRIMARY KEY,
  tipo           text NOT NULL,           -- foto ou fusao
  sessao_id      <FK sessao> NOT NULL,
  foto_id        uuid REFERENCES foto_estetica(id),
  status         text NOT NULL,
  tentativas     int NOT NULL DEFAULT 0,
  worker_id      text,
  reservada_ate  timestamptz,
  resultado      jsonb,
  erro           text,
  criada_em      timestamptz NOT NULL DEFAULT now(),
  atualizada_em  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON tarefa_visao (status, criada_em);

CREATE TABLE sugestao_estetica (
  id               uuid PRIMARY KEY,
  sessao_id        <FK sessao> NOT NULL,
  nota_final       char(1) NOT NULL,
  notas_por_face   jsonb NOT NULL,
  justificativas   jsonb NOT NULL,        -- frases por face
  margens          jsonb NOT NULL,        -- distância das medidas aos limites (seção 16)
  pendencias       jsonb NOT NULL,        -- regras "a definir" ou anomalias que exigem humano
  versao_visao     text NOT NULL,
  versao_criterio  text NOT NULL,
  modelos          jsonb NOT NULL,        -- versões e hashes
  tempo_ms         int NOT NULL,
  criada_em        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE avaliacao_estetica (       -- só INSERT; correção = nova linha com substitui_id
  id               uuid PRIMARY KEY,
  sessao_id        <FK sessao> NOT NULL,
  registro_id      <FK registro>,
  nota_final       char(1) NOT NULL,
  notas_por_face   jsonb NOT NULL,
  nota_regra       char(1) NOT NULL,      -- o que o critério dá com os defeitos confirmados
  justificativa    text,                  -- obrigatória se nota_final ≠ nota_regra
  origem           text NOT NULL,         -- OrigemNota
  cega             boolean NOT NULL,
  tecnico_id       <FK usuario>,
  sugestao_id      uuid REFERENCES sugestao_estetica(id),
  versao_criterio  text NOT NULL,
  versao_visao     text,
  substitui_id     uuid REFERENCES avaliacao_estetica(id),
  criada_em        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE defeito_estetico (
  id                 uuid PRIMARY KEY,
  sessao_id          <FK sessao> NOT NULL,
  face               text NOT NULL,
  foto_id            uuid REFERENCES foto_estetica(id),   -- foto principal
  fotos              jsonb,                               -- todas as fotos em que aparece
  sugestao_id        uuid REFERENCES sugestao_estetica(id),
  avaliacao_id       uuid REFERENCES avaliacao_estetica(id),
  proposta_id        uuid REFERENCES defeito_estetico(id),  -- cópia ligada à proposta da máquina
  tipo               text NOT NULL,
  zona               text NOT NULL,
  visibilidade       text NOT NULL,
  origem             text NOT NULL,       -- OrigemDefeito
  estado             text NOT NULL,       -- EstadoDefeito
  caixa_mm           jsonb NOT NULL,
  geometria_mm       jsonb,
  comprimento_mm     double precision,
  area_mm2           double precision,
  maior_dimensao_mm  double precision,
  confianca          double precision,
  fonte              text NOT NULL,       -- opencv_riscos, patchcore, detector ou tecnico
  criado_em          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON defeito_estetico (sessao_id);

CREATE TABLE evento_sessao (
  id         bigserial PRIMARY KEY,
  sessao_id  <FK sessao> NOT NULL,
  tipo       text NOT NULL,
  dados      jsonb NOT NULL,
  criado_em  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON evento_sessao (sessao_id, id);

CREATE TABLE config_estetica_loja (
  loja_id          <FK loja> PRIMARY KEY,
  modo             text NOT NULL DEFAULT 'desligado',
  percentual_cego  numeric NOT NULL DEFAULT 100,
  atualizado_por   <FK usuario>,
  atualizado_em    timestamptz NOT NULL DEFAULT now()
);
```

**Defeitos:** as propostas da máquina ficam com `sugestao_id` e `estado = proposto` e **nunca mudam**. Ao salvar a avaliação final, o backend grava uma cópia de cada proposta com `avaliacao_id`, `proposta_id` e `estado` `confirmado` ou `rejeitado`, mais os defeitos desenhados pelo técnico (`origem = tecnico`). Assim cada avaliação guarda o retrato exato do que foi decidido, e as propostas rejeitadas viram exemplos negativos no treino.

### 7.9 Resultado do worker

Resultado de uma tarefa `foto`:

```json
{
  "tarefa_id": "t1…", "tipo": "foto", "foto_id": "f1…",
  "versao_visao": "0.3.0",
  "qualidade": {"ok": true, "nitidez": 812.4, "estouro_pct": 0.02, "contorno_ok": true, "motivo": null},
  "faces_extraidas": [
    {"face": "frente",
     "cantos_px": [[1012.5, 402.1], [7051.2, 410.8], [7044.9, 3519.0], [1006.3, 3510.7]],
     "homografia": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
     "mm_por_px": 0.0452, "residuo_bordas_mm": 0.12, "orientacao_ok": true}
  ],
  "deteccoes": [
    {"face": "frente", "fonte": "opencv_riscos", "tipo": "risco", "zona": "tela",
     "geometria_mm": {"tipo": "polilinha", "pontos": [[10.2, 33.1], [18.9, 41.0]]},
     "caixa_mm": [10.2, 33.1, 8.7, 7.9], "comprimento_mm": 11.8,
     "contraste_rasante": 0.31, "confianca": 0.82}
  ],
  "artefatos": {"retificada": true, "anotada": true},
  "tempo_ms": 1840
}
```

Resultado de uma tarefa `fusao`:

```json
{
  "tarefa_id": "t9…", "tipo": "fusao", "sessao_id": "8f1c…",
  "versao_visao": "0.3.0",
  "modelos": {"detector": "rfdetr-s-defeitos-v2+a1b2c3d", "patchcore": {"vidro_fosco_escuro": "pc-v1+d4e5f6a"}},
  "defeitos": [
    {"face": "frente", "tipo": "risco", "zona": "tela", "visibilidade": "so_rasante",
     "foto_principal": "f1…", "fotos": ["f1…", "f2…"],
     "caixa_mm": [10.2, 33.1, 8.7, 7.9],
     "geometria_mm": {"tipo": "polilinha", "pontos": [[10.2, 33.1], [18.9, 41.0]]},
     "comprimento_mm": 11.8, "area_mm2": null, "maior_dimensao_mm": 11.8,
     "confianca": 0.86, "fonte": "opencv_riscos"}
  ],
  "faces_sem_foto_valida": [],
  "tempo_ms": 620
}
```

Com o resultado da fusão, o backend roda o critério (seção 16), grava `sugestao_estetica` e as propostas em `defeito_estetico`, e emite `sugestao_pronta`.

### 7.10 ESP32 (`hardware/cabine-luz/`)

HTTP na rede local. Nome mDNS `morecheck-cabine-<n>.local`, serviço `_http._tcp` com TXT `tipo=cabine-luz`. Cabeçalho `X-Chave-Cabine` obrigatório (valor em `include/segredos.h`). Substitui o `POST /luz {"rasante": …, "ambiente": …}` do PRD, por causa de R1 e D4.

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /estado` | — | `{"canais": {"a": 0, "b": 0, "difusa": 0, "contraluz": 0}, "versao": "1.0.0", "uptime_s": 1234}` |
| `POST /luz` | `{"a": 100, "b": 0}` (0–100; canal omitido = sem mudança) | `200` com o estado **depois** de aplicar (resposta síncrona) |
| `POST /desligar` | — | `200`, todos os canais em 0 |

Mapa luz → canais: `ambiente` = tudo apagado (ou só `difusa`, se existir); `rasante_a` = `a`; `rasante_b` = `b`; `rasante_ab` = `a` + `b`; `contraluz` = só `contraluz`.

Requisitos: PWM a ≥ 20 kHz (evita faixas na foto) e 100% durante as fotos; desliga tudo sozinho após 120 s sem comando; LED da placa pisca até conectar ao Wi-Fi.

### 7.11 Perfil de calibração da cabine

Gerado no app (seção 14.3), guardado no aparelho e enviado como referência em cada foto (`perfil_calibracao_versao`) e na tarefa do worker.

```json
{
  "versao": 3,
  "criado_em": "2026-10-20T09:12:00-03:00",
  "camera_modelo": "iPhone15,3",
  "dimensoes_px": {"largura": 8064, "altura": 6048},
  "exposicao": {"ambiente": {"duracao_s": 0.016667, "iso": 125},
                "rasante":  {"duracao_s": 0.016667, "iso": 64},
                "contraluz":{"duracao_s": 0.016667, "iso": 32}},
  "balanco_branco": {"r": 1.92, "g": 1.0, "b": 1.71},
  "foco": {"deitado": 0.62, "lateral": 0.48, "ponta": 0.40},
  "px_por_mm_berco": 22.1,
  "orientacao": {"deitado": "topo_para_esquerda"},
  "regiao_berco_px": [900, 300, 6300, 5200],
  "regioes_espelho_px": {"lat_esq": [[0, 0], [0, 0], [0, 0], [0, 0]]}
}
```

### 7.12 Variáveis de ambiente

Todos os segredos ficam em `~/.morecheck/producao.env`. Siga a convenção de carregamento que o backend já usa.

| Variável | Onde | Exemplo | Uso |
|---|---|---|---|
| `ESTETICA_ARMAZENAMENTO` | backend | `s3` | `disco` ou `s3` |
| `ESTETICA_DIR_FOTOS` | backend | `/dados/fotos` | só no modo disco |
| `S3_ENDPOINT_URL` | backend | `https://<conta>.r2.cloudflarestorage.com` | R2 ou S3 |
| `S3_BUCKET_ESTETICA` | backend | `morecheck-estetica` | |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | backend | segredo | |
| `ESTETICA_TAMANHO_MAX_MB` | backend | `40` | |
| `ESTETICA_RETENCAO_MESES` | backend | `12` | |
| `VISAO_WORKER_TOKENS` | backend | segredo (lista separada por vírgula) | autentica workers |
| `MORECHECK_API_URL` | worker | `https://api-check.more-megastore.com` | |
| `VISAO_WORKER_TOKEN` | worker | segredo | |
| `VISAO_WORKER_ID` | worker | `mac-loja-1` | |
| `VISAO_DISPOSITIVO` | worker | `mps` | `cpu`, `mps` ou `cuda` |
| `VISAO_DIR_MODELOS` | worker | `~/.morecheck/modelos` | |
| `ROBOFLOW_API_KEY` | ferramentas | segredo | baixar bases |

### 7.13 Acréscimos da implementação (2026-10-16)

Mudanças nos contratos feitas durante a implementação (registradas em `design.md`). Valem junto com 7.1 a 7.12.

**Cabine (7.3)**
- `GET /cabine/{token}` responde `403` se a nota estética estiver `desligado` na loja.
- `POST /cabine/{token}/fotos`: arquivo maior que `ESTETICA_TAMANHO_MAX_MB` → `413`; bytes que não são HEIC, JPEG ou DNG → `422`. Uma foto nova depois de `concluir` (refazer) volta a sessão para `capturando` e cancela a fusão pendente.
- **Novo** `PUT /cabine/perfil` (token da cabine): corpo = perfil 7.11. Guardado em `cabine.perfil_calibracao` e enviado ao worker em cada tarefa.
- **Novo** `GET /cabine/{token}/eventos?apos={seq}`: long-poll com o formato de 7.4, tipos `foto_reprovada` e `sugestao_pronta`.
- **Novo** `GET /cabines` (admin) lista as cabines da loja.
- Pareamento: o QR mostrado no painel contém `{"api": "<url>", "codigo": "K7PQ-3XWD"}`. O app aceita também o código digitado.

**Worker (7.6 e 7.9)**
- `upload` é por face: `{"retificada": {"frente": "url", "lat_esq": "url", …}, "anotada": {…}}`, porque com espelhos uma foto tem várias faces. Os arquivos ficam em `sessoes/{sessao}/{retificada|anotada}/{foto_id}_{face}.jpg`; `foto_estetica.chave_retificada` guarda o prefixo sem `_{face}.jpg`.
- `fotos_irmas[]` inclui `formato`.
- Tarefa `fusao` entregue ao worker: `{tarefa_id, tipo, sessao_id, lease_ate, aparelho, config, roteiro, fotos: [{foto_id, passo, face, faces, luz, pose, lado, aceita, resultado}]}`, com `resultado` = o resultado da tarefa `foto` (7.9) ou `null`. Vai só a última tentativa de cada passo e luz.
- `POST /visao/tarefas/{id}/falha` aceita `worker_id` (opcional).
- As detecções do worker trazem `contraste_ambiente` (em MADs). A fusão marca `visivel` quando o contraste ≥ `T_VISIVEL` (`visao/src/visao/config.py`).

**Tabelas (7.8)**
- `cabine.perfil_calibracao jsonb`.
- Nova tabela `cabine_pareamento (id, loja_id, codigo_hash, criado_por, expira_em, usado_em)`.
- `sessao_estetica.conjunto text` (`treino`, `validacao` ou `teste`): fixo por aparelho, pelo hash SHA-256 do IMEI. O `teste` é o holdout do gate (13.1) e nunca entra no treino.
- `foto_estetica.original_apagada_em` (retenção).
- `config_estetica_loja.sombra_iniciada_em` (início do modo sombra, 13.2).
- `avaliacao_estetica` tem `CHECK (nota_final = nota_regra OR justificativa IS NOT NULL)`.

**Regras**
- Avaliação de sessão cega ainda sem avaliação: as propostas da máquina não entram (nem como confirmadas, nem como rejeitadas) e a origem é sempre `tecnico`.
- A automação seletiva (13.3) nunca automatiza uma sessão cega: ela é a amostra de monitoramento.
- O gate (13.1) é medido por loja (todas as famílias juntas). A visão por família fica no relatório de concordância.

**Variáveis de ambiente (7.12)**

| Variável | Onde | Padrão | Uso |
|---|---|---|---|
| `DATABASE_URL` | backend | `postgresql+psycopg://localhost/morecheck_dev` | banco |
| `URL_PUBLICA` | backend | `http://localhost:8000` | base das URLs assinadas no modo disco |
| `ESTETICA_SEGREDO_URLS` | backend | segredo | assinatura HMAC das URLs no modo disco |
| `ESTETICA_URL_EXPIRA_S` | backend | `900` | validade das URLs assinadas |
| `ESTETICA_ROTEIRO` | backend | `roteiro-v1` | `roteiro-v1` (espelhos) ou `roteiro-v1-em-pe` (D3) |
| `ESTETICA_RASANTE_JUNTAS` | backend | `false` | `true` = uma foto `rasante_ab` (D1) |
| `ESTETICA_CONTRALUZ` | backend | `false` | foto de contraluz no roteiro (D4) |
| `ESTETICA_LEASE_S`, `ESTETICA_TENTATIVAS_MAX` | backend | `120`, `3` | fila |
| `ESTETICA_LONG_POLL_S` | backend | `25` | long-poll |
| `ESTETICA_KAPPA_TECNICOS` | backend | — | kappa técnico × técnico da fase 1 (linha de base do gate) |
| `ESTETICA_PERCENTUAL_HOLDOUT` | backend | `10` | % dos aparelhos no conjunto de teste |

---

## 8. Fase 0 — Teste na mão

**Esforço:** 1 dia (metade humano, metade Claude Code). **Pré-requisito:** nenhum.

### 8.1 Objetivo

Responder com números, antes de comprar ou imprimir qualquer coisa:

| # | Pergunta | Decide |
|---|---|---|
| P1 | A luz rasante mostra os riscos que a bancada considera? Uma direção basta? | D1, R1 |
| P2 | Quantos px/mm temos a cada altura e quantos precisamos para não perder microrriscos? | D2, R4, R5 |
| P3 | Quanto a nitidez cai com a face fora do plano de foco? Os espelhos a 45° dão bordas nítidas? | D3, R2, R3 |
| P4 | O contorno sai bem em fundo preto, inclusive com aparelho preto? A contraluz ajuda? | D4, R16 |
| P5 | O algoritmo clássico separa risco de poeira, digital e reflexo? | R6 |
| P6 | Qual o tamanho real de cada foto? | D8, R12 |

### 8.2 O que o humano faz

**Material:**
- iPhone para fotografar, de preferência Pro (48 MP e ProRAW); se possível, o mesmo modelo que será a câmera da cabine;
- apoio fixo: tripé com garra de celular (~R$ 30) ou uma pilha de livros com o celular apoiado na beirada;
- lanterna de outro celular;
- régua;
- folha de marcadores ArUco (gerada pelo Claude Code, passo 2 da seção 8.3);
- pano ou cartolina preta fosca;
- um tablet ou celular com a tela toda branca (teste de contraluz);
- um espelho pequeno e massa de modelar para incliná-lo a 45° (espelho de estojo serve para o teste; na cabine, espelho de primeira superfície evita imagem dupla);
- pano de microfibra;
- 3 a 5 aparelhos variados: 1 quase perfeito, 1 com riscos finos, 1 com riscos visíveis, 1 com marca ou amassado na moldura, 1 trincado se houver. Pelo menos um deles preto.

**Protocolo** (o Claude Code mostra este protocolo ao humano antes de começar):
1. Imprima `visao/prototipos/saida/marcadores.pdf` em 100% (sem "ajustar à página"). Confira com a régua que cada quadrado tem 30,0 mm.
2. Prenda o iPhone olhando para baixo, paralelo à mesa, com **25 cm** da lente até a mesa. **Não fotografe com o celular na mão**: as fotos de luz ambiente e rasante de uma face precisam ficar alinhadas pixel a pixel.
3. App Câmera, lente 1x, sem flash. Formato ProRAW 48 MP se houver (arquivos grandes, tudo bem no teste); senão HEIF 48 MP. Toque e segure no aparelho para travar foco e exposição.
4. Limpe o aparelho com a microfibra. Coloque-o sobre o pano preto, com a folha de marcadores ao lado.
5. Para cada aparelho, sem mexer em nada entre as fotos da mesma face:
   - **frente:** `amb` (luz da sala); `ra` (lanterna rente à mesa, 1–2 cm de altura, a ~20 cm do aparelho, apontada ao longo do comprimento); `rb` (o mesmo, apontada ao longo da largura); `sil` (aparelho sobre o tablet de tela branca, com a luz da sala apagada se possível);
   - **traseira:** `amb`, `ra`, `rb`;
   - **uma lateral**, com o aparelho em pé apoiado: `amb`, `ra`.
6. **Teste de foco:** com o foco travado no aparelho deitado, tire uma foto do mesmo aparelho em pé de lado (`foco_lateral`) e outra em pé na ponta (`foco_ponta`), sem tocar na tela para refocar.
7. **Teste de espelho:** aparelho deitado, espelho inclinado a 45° encostado numa lateral, foco travado no aparelho: fotos `espelho_amb` e `espelho_ra`.
8. **Teste de poeira (opcional):** uma foto `ra` da frente **antes** de limpar (`sujo_ra`).
9. Nomeie os arquivos `ap{n}_{face}_{luz}.{ext}`. Exemplos: `ap2_frente_ra.dng`, `ap2_lat_amb.heic`, `ap1_foco_ponta.heic`.
10. Preencha `anotacao.csv` com o que o técnico vê em cada aparelho: `aparelho,modelo,cor,face,tipo,local,tamanho_mm_aprox,visivel_olho_nu,nota_tecnico`.
11. Copie tudo para `visao/prototipos/fotos/`.

### 8.3 O que o Claude Code faz

1. Criar `visao/` com `uv init --package visao` (VERIFICAR a versão do Python do backend e usar a mesma). Dependências: `opencv-contrib-python`, `scikit-image`, `numpy`, `pillow`, `pillow-heif`, `rawpy`, `matplotlib`. Pôr `prototipos/fotos/` e `prototipos/saida/` no `.gitignore`.
2. `gerar_marcadores.py` → `prototipos/saida/marcadores.pdf`: 4 marcadores `DICT_4X4_50` (ids 0–3) de 30 mm, margem branca de 5 mm, PDF A4 em escala 1:1, com uma régua de 100 mm desenhada para conferência.
3. `src/visao/io_imagem.py`: ler HEIC (`pillow-heif`, mantendo 16 bits se houver), DNG (`rawpy`, demosaico sem brilho automático) e JPEG; **ignorar a orientação EXIF**; devolver `float32` de 0 a 1, em tons de cinza e em cor.
4. `medir_escala.py`: mm/px pelos ArUco e pelo contorno do aparelho (seção 15.3), usando as dimensões do modelo; mostrar a diferença, com e sem a foto `sil`.
5. `riscos.py`: camada (a) da seção 15.4 sobre `ra`, `rb` e a união das duas; salvar sobreposições coloridas e uma tabela com cada risco (comprimento em mm, direção, contraste).
6. `comparar_iluminacao.py`: quanto do comprimento total de risco aparece só em `ra`, só em `rb` e nas duas; o mesmo em número de riscos.
7. `comparar_resolucao.py`: rodar a detecção na resolução nativa e reamostrada para 10, 15 e 20 px/mm; mostrar os riscos perdidos por faixa de comprimento (< 3 mm, 3–5, 5–15, > 15).
8. `profundidade_foco.py`: nitidez (variância do Laplaciano e largura de borda 10–90% numa aresta do aparelho) em deitado × `foco_lateral` × `foco_ponta` × `espelho_amb`.
9. Cruzar as detecções com `anotacao.csv` numa tabela "o técnico viu × o algoritmo achou", e comparar `sujo_ra` com a foto limpa.
10. Calcular, para a altura usada: px/mm medido, campo de visão útil e a altura que daria 20 px/mm. Referência: a 1x, a largura do campo é ~1,44 × a distância, para 8064 px (25 cm → ~22 px/mm; 35 cm → ~16 px/mm).
11. `relatorio.py` → `docs/nota-estetica-fase0-relatorio.md` com: respostas P1 a P6 com números e imagens; recomendação para D1 a D4; limiares iniciais da camada (a); tamanho médio das fotos e estimativa de armazenamento por mês; lista de surpresas.

### 8.4 Pronto quando

- Riscos visíveis na luz rasante e detectados pelo OpenCV (critério do PRD).
- P1 a P6 respondidas com números e imagens no relatório.

**PARADA:** apresente o relatório. O responsável decide D1 a D4. Registre em `design.md` e, se algo do PRD mudar, proponha o texto da versão 1.1.

---

## 9. Fase 1 — Critério de nota

**Esforço:** 4–6 h de Claude Code + 1 reunião. **Pré-requisito:** fotos da fase 0 (para os exemplos).

### 9.1 Objetivo

Um critério escrito, medível e aprovado (`criterio-v1`), e a concordância técnico × técnico medida. Ela vira a **linha de base humana** da fase 5.

### 9.2 O que o Claude Code faz

1. Redigir `docs/nota-estetica-criterio.md` a partir do PRD §10, com:
   - faces e zonas, com um desenho das zonas sobre o aparelho e o referencial da seção 7.2;
   - tipos de defeito, cada um com uma foto de exemplo da fase 0;
   - **como medir:** risco = comprimento do traço; amassado = diâmetro aparente na luz rasante; lascado = maior dimensão; mancha e descascado = área;
   - "visível" = visto a olho nu a ~30 cm sob a luz da bancada; "só rasante" = só aparece com luz rasante (R9);
   - tabela de regras por **grupo de zona** (tela, traseira, moldura); a nota da face é a pior entre os grupos dela;
   - regras gerais; o que fazer com película, capa e sujeira (retirar e limpar antes);
   - exemplos resolvidos (cada um vira um teste do motor);
   - lacunas (seção 16.4, decisão D5), marcadas "a definir", com uma proposta para cada uma.
2. Escrever `backend/app/estetica/criterios/criterio-v1.yaml` e o motor `backend/app/estetica/criterio.py` (seção 16), com testes. O motor não depende da visão e pode ser feito já.
3. Criar `docs/estudo-concordancia-v1.csv` (modelo): `aparelho_id,modelo,cor,tecnico,face,nota,observacao`. Cada técnico preenche a própria cópia **sem ver a do outro**.
4. `visao/ferramentas/concordancia.py` (adicionar `scikit-learn` ao pacote): concordância exata, ±1, quantidade de casos a ≥ 2 notas, **kappa ponderado quadrático** (`sklearn.metrics.cohen_kappa_score(..., weights="quadratic")`), matriz de confusão 4×4 por face e na nota final, e a lista das divergências para levar à reunião.

### 9.3 O que o humano faz

- Separar 20 aparelhos com pelo menos 4 de cada nota (se faltar nota D, pelo menos 2).
- Dois técnicos avaliam os mesmos 20 aparelhos, cada um sozinho, usando o documento.
- Reunião para discutir as divergências; o Claude Code reescreve as regras; repetir até concordarem.

### 9.4 Pronto quando

- Concordância exata ≥ 85% na nota final (PRD) **e** kappa ponderado ≥ 0,80.
- Documento aprovado como `criterio-v1`; YAML e testes do motor batendo com os exemplos do documento.

**PARADA:** aprovação do critério pelo responsável. Guardar os números do estudo: eles são a linha de base da seção 13.

---

## 10. Fase 2 — Cabine A

**Esforço:** 1 dia de montagem + 12–16 h de código. **Pré-requisitos:** D1 a D4 decididas; `criterio-v1` aprovado.

### 10.1 Hardware (`hardware/cabine-a/`)

**Claude Code:**
1. `README.md` com:
   - lista de compras: EVA preto fosco 40×40 cm com furo de ~3 cm para a lente; 2 barras de LED 5000 K de 12 V (~30 cm, com difusor); ESP32 DevKit; MOSFETs que conduzam bem com 3,3 V no gate (ex.: IRLB8721 ou AO3400) ou um módulo MOSFET de 4 canais próprio para 3,3 V; fonte de 12 V e 2 A; alimentação USB para o ESP32; braço articulado; feltro para as áreas de apoio; opcionais conforme as decisões: painel de LED A4 para contraluz (D4), espelhos de primeira superfície (D3), painel difuso para luz de cima;
   - montagem: altura da câmera (D2), barras a 1–2 cm da mesa e à distância medida na fase 0, como conferir o paralelismo da câmera (app de nível do celular), como posicionar o anteparo;
   - ligação elétrica (texto ou diagrama simples): fonte → MOSFET → fita; GPIO do ESP32 → gate com resistor de 220 Ω; resistor de 10 kΩ do gate ao GND; GND comum;
   - conferências finais, cada uma com o resultado esperado.
2. `berco.scad` paramétrico (variáveis no topo do arquivo): placa de ~250×200 mm; **batente em L com altura ≤ 3 mm**, para não fazer sombra na luz rasante; bolsões de 30×30 mm para os ArUco; encaixes das barras de LED; rebaixo para feltro nas áreas de apoio; conforme D3, encaixes para os espelhos a 45° ou suportes para as poses `lateral` e `ponta`. Exportar STL com `openscad -o berco.stl berco.scad` (VERIFICAR se o `openscad` está instalado; se não estiver, entregar o `.scad` e pedir ao humano para exportar).
3. Reaproveitar `gerar_marcadores.py` para `marcadores-aruco.pdf`.

**Humano:** compra, imprime, monta e manda fotos da montagem.

### 10.2 Firmware do ESP32 (`hardware/cabine-luz/`)

**Claude Code:**
1. Projeto PlatformIO, framework Arduino; bibliotecas `WiFi`, `WebServer`, `ESPmDNS` e `ArduinoJson` (VERIFICAR a versão disponível).
2. Saídas PWM com LEDC: 20 kHz, 10 bits, um canal por saída (`a`, `b`, `difusa`, `contraluz`). Pinos configuráveis no topo de `main.cpp`.
3. API da seção 7.10, cabeçalho `X-Chave-Cabine`, desligamento automático após 120 s sem comando, LED da placa piscando até conectar.
4. `include/segredos.exemplo.h` com SSID, senha, chave da cabine e nome mDNS; `include/segredos.h` no `.gitignore`.
5. `README.md` com: como copiar `segredos.exemplo.h`, gravar (`pio run -t upload`), descobrir o IP e testar:

   ```bash
   curl -X POST http://morecheck-cabine-1.local/luz \
     -H 'X-Chave-Cabine: <chave>' -H 'Content-Type: application/json' -d '{"a":100}'
   ```

**Humano:** grava o ESP32 (ou o Claude Code, se a placa estiver ligada à máquina em que ele roda) e testa os canais.

### 10.3 App modo Cabine (iPhone câmera)

Leia antes a seção 14 inteira.

**Claude Code:**
1. Ler `app-ios/`: `project.yml` (xcodegen), `LeitorQR.swift`, `Envio.swift`, `Testes/Sujeira.swift` e os padrões de rede, UI e persistência. VERIFICAR a versão mínima do iOS do projeto.
2. **Entrada:** "Modo Cabine" fora do fluxo normal de testes (ex.: dentro de configurações), liberado só depois do pareamento (D10).
3. **Pareamento:** ler o QR de pareamento do painel → `POST /cabines/ativar` → token no Keychain.
4. **Calibração** (assistente; refazer sempre que a cabine for mexida): seção 14.3. Salva o `PerfilCamera` (seção 7.11).
5. **Máquina de estados do roteiro** (seção 14.5). Tela grande com a face pedida, o progresso, o estado das luzes e da fila de envio. Voz curta opcional (`AVSpeechSynthesizer`, pt-BR).
6. **Captura:** seções 14.2 e 14.4.
7. **Estabilidade e qualidade local:** seção 14.6.
8. **Envio:** fila persistida em disco no padrão de `Envio.swift`, reenvio com espera crescente, `Idempotency-Key` por foto, envio durante a captura (não no fim).
9. **Fim:** `POST /concluir`; consultar `GET /sugestao`; mostrar o resumo se `mostrar = true` (a confirmação da nota fica no painel, D9); pedir para refazer as faces listadas em `refazer`; botão "Próximo aparelho".
10. **`project.yml`:** `NSCameraUsageDescription`, `NSLocalNetworkUsageDescription`, `NSAppTransportSecurity` → `NSAllowsLocalNetworking = true` (HTTP sem TLS só na rede local) e `NSBonjourServices = ["_http._tcp"]` se usar `NWBrowser`. No modo Cabine: `isIdleTimerDisabled = true` e orientação travada.
11. Rodar `xcodegen generate`; compilar com `xcodebuild -scheme <esquema> -destination 'generic/platform=iOS' build`; testar a lógica pura (máquina de estados, detector de estabilidade) no simulador (VERIFICAR o nome com `xcrun simctl list devices`). A câmera não funciona no simulador.

**PARADA:** o humano instala no iPhone câmera, calibra e testa com 3 aparelhos seguindo o checklist da seção 17.2.

### 10.4 Tela QR + preto (aparelho avaliado)

**App nativo (preferido):**
- ao fim dos testes funcionais, tela "Estética" com o QR da sessão em tela cheia e long-poll de eventos (seção 7.4);
- evento `preto`: view preta em tela cheia; esconder barra de status e indicador de início (SwiftUI: `.statusBarHidden()` e `.persistentSystemOverlays(.hidden)`; UIKit: `prefersStatusBarHidden` e `prefersHomeIndicatorAutoHidden`); guardar o brilho atual e pôr o brilho em 0 pela tela da cena (`windowScene.screen.brightness`, porque `UIScreen.main` está obsoleto); `isIdleTimerDisabled = true`;
- evento `qr`: volta o QR; evento `normal` ou saída da tela: restaura o brilho e o bloqueio automático;
- sem rede: mostrar instrução para o técnico apagar a tela manualmente (travar o aparelho).

**Página de testes (alternativa):** fundo `#000`, Wake Lock API (`navigator.wakeLock.request("screen")`) e o mesmo long-poll. Limitações: não controla o brilho e o Safari mantém barras na tela. Use só se o app nativo não estiver disponível.

### 10.5 Pronto quando

- Todas as fotos do roteiro em ≤ 60 s por aparelho (mediana de 10 aparelhos, com o técnico real).
- ≥ 95% das fotos aceitas na primeira tentativa.
- Envio completo ≤ 10 s após a última foto, na rede da loja.
- O aparelho avaliado apaga a tela em ≤ 2 s após o pedido.
- Os metadados de 10 sessões seguidas mostram ISO, tempo de exposição, foco e balanço de branco **idênticos** dentro de cada combinação de luz e pose.

**PARADA:** medir com o técnico real e ajustar o roteiro antes da fase 3.

---

## 11. Fase 3 — Backend, painel e laudo

**Esforço:** 16–24 h. **Pré-requisitos:** D8, D10, D11 e D12 decididas (ou PADRÃO).

### 11.1 Backend (`backend/app/estetica/`)

1. Explorar `backend/` antes de escrever: autenticação, escopo por loja, auditoria, `rotas/sessoes.py` (como a sessão e o token funcionam e onde ficam modelo e IMEI), convenções de Alembic e de testes. VERIFICAR se já existe WebSocket.
2. Migração Alembic com as tabelas da seção 7.8, com `downgrade`.
3. `dimensoes.py` (Apêndice A), começando pelos modelos de maior volume. Para saber quais são, consulte as sessões no banco de desenvolvimento ou pergunte ao responsável.
4. `armazenamento.py`: interface `salvar`, `url_leitura(expira)`, `url_escrita(expira)`, `apagar`; implementações `disco` (desenvolvimento) e `s3` (`boto3` com `endpoint_url`, compatível com R2). Antes de usar disco em produção, o humano confere o espaço com `df -h` na VPS.
5. Rotas das seções 7.3 a 7.6 com validação (tamanho ≤ 40 MB, formato, enums), escopo por loja e auditoria.
6. Fila: reserva com `SELECT … FOR UPDATE SKIP LOCKED`, prazo de 120 s, até 3 tentativas. A tarefa `foto` de uma luz rasante só é liberada depois que a foto `ambiente` do mesmo passo chegou. A tarefa `fusao` só é liberada quando todas as tarefas `foto` da sessão terminarem.
7. Eventos: tabela + long-poll (consulta a cada 500 ms, até 25 s).
8. Motor de critério ligado ao resultado da fusão → `sugestao_estetica`; rota `POST /estetica/criterio/avaliar` para o painel.
9. Amostra cega: sorteio ao criar `sessao_estetica`, com o `percentual_cego` da loja. A API esconde a sugestão enquanto a sessão for cega e não tiver avaliação final, inclusive na cabine.
10. Worker nulo (`worker.py --nulo` no pacote `visao`): devolve qualidade ok, geometria vazia e zero defeitos. Permite testar o fluxo inteiro antes da fase 4.
11. Retenção (`retencao.py`, diária): apagar originais com mais de `ESTETICA_RETENCAO_MESES`, exceto fotos com defeito confirmado; registrar o que foi apagado.

### 11.2 Painel — tela de avaliação

Siga o guia visual "morecheck-sistema" (amarelo `#F5C400`, tinta `#15191E`, Archivo e IBM Plex) e os padrões do painel.

- **Fila:** sessões aguardando técnico, com modelo, hora, status da sugestão e selo "cega".
- **Layout:**
  - esquerda: miniaturas das faces com a nota de cada uma;
  - centro: visualizador da face retificada com zoom e arrasto (o zoom 1:1 é obrigatório para ver microrriscos) e camadas alternáveis (ambiente, rasante a, rasante b, defeitos, mapa de anomalia);
  - direita: lista de defeitos da face (confirmar ou rejeitar, mudar tipo e zona, medida em mm), nota da face (A–D), "nota pela regra" × "sua nota".
- **Desenhar defeito:** arrastar uma caixa (ou traçar uma linha, para risco) sobre a imagem retificada; o painel converte para mm e pergunta o tipo.
- **Nota final:** calculada pela regra (pior face + regras gerais) a cada mudança, via `POST /estetica/criterio/avaliar`. O técnico pode mudá-la, com justificativa obrigatória.
- **Sessão cega:** não mostra sugestão nem defeitos da máquina até salvar; depois de salvar, mostra a comparação (serve de retorno para o técnico).
- **Atalhos de teclado:** `1`–`6` escolhe a face; `A`/`B`/`C`/`D` dá a nota da face; `espaço` alterna a camada; `X` rejeita o defeito selecionado; `N` desenha um defeito novo; `Enter` salva.
- **Meta:** avaliar uma sessão em < 30 s quando a sugestão estiver certa.

### 11.3 Painel — relatório de concordância

- Filtros: período, loja, modelo, face, técnico; "incluir sessões não cegas" desligado por padrão, com aviso quando ligado.
- Indicadores: concordância exata, ±1, quantidade de casos a ≥ 2 notas, kappa ponderado com intervalo de confiança de 95% (bootstrap), recall por nota, matriz de confusão 4×4 (nota final e por face), evolução por semana.
- Lista dos casos discordantes, com link para a sessão.
- Situação do gate da seção 13 por família de modelo.

### 11.4 Laudo

- Bloco "Estado estético" no PDF: nota final em destaque, origem (`tecnico`, `sugerida` ou `automatica`), miniaturas das faces na luz ambiente, lista de defeitos (tipo, face, zona, medida) e versão do critério.
- Página de verificação (QR do laudo): conforme D11.
- Seguir o estilo do laudo atual em `backend/app/laudo/`.

### 11.5 Pronto quando

- O técnico avalia pelo painel e a nota sai no laudo (critério do PRD).
- Testes de rotas, idempotência, escopo por loja, amostra cega e fila passando; a migração sobe e desce.
- Fluxo ponta a ponta com o worker nulo e as fotos da fase 0 (`simular_cabine.py`, seção 17.3) funcionando.

**PARADA:** o técnico usa o painel em 10 sessões reais e dá retorno sobre a tela.

---

## 12. Fase 4 — Nota sugerida

**Esforço:** 16–24 h + uso real. **Pré-requisitos:** D6 e D7 decididas; fase 3 em uso.

### 12.1 Ordem de construção

1. Worker real: reservar, baixar, renovar, enviar resultado e tratar falha (`cliente_api.py`, `worker.py`).
2. Qualidade, geometria e retificação (seções 15.2 e 15.3).
3. Camada (a) riscos + visibilidade + fusão + medição + zonas (seções 15.4, 15.5, 15.8 e 15.9). Isso já gera sugestão para a tela.
4. Relatório de concordância rodando com dados reais.
5. Camada (c) detector: pré-treino com bases públicas, depois ajuste fino com as marcações do painel (seções 12.3 e 15.7).
6. Camada (b) PatchCore, quando houver ≥ 100 faces nota A por família de acabamento (seção 15.6).

### 12.2 Worker

- Configuração pelas variáveis da seção 7.12; log estruturado com `tarefa_id`, tempo por etapa e versão.
- `VISAO_DISPOSITIVO` define `cpu`, `mps` ou `cuda`; os modelos são carregados uma vez e mantidos em memória.
- Renovar a reserva a cada 60 s em tarefas longas.
- Imagem ilegível ou contorno não encontrado = resultado com `qualidade.ok = false` e motivo (não é falha da tarefa). Exceção inesperada = `POST /falha`.
- Rodar como serviço (launchd no Mac ou systemd na VPS); o `README.md` explica como.

### 12.3 Bases públicas e pré-treino do detector

1. Baixar só as bases permitidas na seção 18, com `ferramentas/baixar_bases.py`, em formato COCO. Registrar em `DATASETS.md`: URL, licença, atribuição, data do download e número de imagens.
2. Unificar as classes para o enum `TipoDefeito` conforme a seção 18.2.
3. Treinar o RF-DETR de base (seção 15.7) e medir nas fotos da fase 0. Espere acerto baixo: as fotos públicas são diferentes das nossas, e o valor do pré-treino é começar à frente.

### 12.4 Dados próprios

- `ferramentas/exportar_dataset.py` gera COCO a partir do banco: positivos = defeitos confirmados e desenhados pelo técnico; negativos difíceis = propostas rejeitadas; imagens = faces retificadas recortadas em blocos.
- **Separar treino, validação e teste por aparelho** (hash do IMEI), nunca por foto: fotos do mesmo aparelho são quase iguais e vazariam entre os conjuntos.
- Congelar um **conjunto de teste fixo** (holdout) que nunca entra no treino. O gate da fase 5 é medido nele.
- Registrar cada modelo treinado em `MODELOS.md`: versão, hash dos pesos, dados usados, métricas e data.

### 12.5 Pronto quando

- Sugestão em ≤ 10 s (p95) após a última foto.
- Mesma entrada → mesma saída (teste de regressão com as fotos da fase 0).
- Testes sintéticos: erro de comprimento ≤ 5% ou ≤ 0,5 mm; ≥ 95% da poeira sintética rejeitada.
- Recall ≥ 90% para riscos ≥ 3 mm marcados pelos técnicos (meta inicial; ajustar com o responsável).
- Relatório de concordância semanal publicado no painel.

**PARADA:** o responsável revisa o relatório de concordância toda semana até a fase 5.

---

## 13. Fase 5 — Modo automático

**Pré-requisito:** fase 4 em uso, com dados suficientes na amostra cega.

### 13.1 Gate (o backend obriga; RF11)

O modo `automatico` só pode ser ligado para uma loja e uma família de modelos se o último relatório, calculado **só com sessões cegas de aparelhos que nunca entraram no treino** (conjunto de teste fixo, seção 12.4), mostrar:

| Métrica | Mínimo |
|---|---|
| Aparelhos avaliados | ≥ 200 |
| Concordância exata na nota final | ≥ 90% (PRD) |
| Casos a ≥ 2 notas de distância | 0 (PRD) |
| Kappa ponderado quadrático | ≥ o kappa técnico × técnico da fase 1 |
| Recall em cada nota (A, B, C e D) | ≥ 80% |

Com 200 aparelhos e zero erros de 2 notas, o máximo que se garante estatisticamente é uma taxa abaixo de ~1,5% (regra de três). O relatório deve dizer isso.

### 13.2 Antes de ligar

**Modo sombra:** 2 semanas com 100% das sessões cegas. A máquina dá a nota, o técnico avalia sem ver, e o relatório compara.

### 13.3 Com o automático ligado

- **Automação seletiva:** a nota só sai automática se nenhuma medida estiver perto de um limite do critério (margem > 10%), nenhuma regra "a definir" tiver sido acionada, não houver defeito `anomalia` e nenhuma detecção de `trinca` tiver confiança intermediária. Senão, a sessão vai para o técnico.
- **Monitoramento:** amostra cega contínua de 5–10%. Se a janela dos últimos 200 aparelhos cair abaixo do gate, o backend volta a loja para `assistido` sozinho e avisa o responsável.
- Gravar `origem = automatica`, `versao_visao` e `versao_criterio` em toda nota (RF9).

**PARADA:** ligar o automático é decisão do responsável, por loja.

---

## 14. Referência: câmera iOS

Os trechos de código são **esboços**. VERIFICAR cada assinatura na versão do SDK do projeto.

### 14.1 Câmera e lente

- Use `AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back)`: a lente principal (1x). Nunca use câmeras virtuais (`builtInTripleCamera`, `builtInDualWideCamera`), porque elas trocam de lente sozinhas (por exemplo, para macro).
- 48 MP: iPhone 14 Pro ou mais novo, incluindo 15, 16 e 17 sem "Pro" (VERIFICAR no modelo escolhido). Escolha o `activeFormat` cujo `supportedMaxPhotoDimensions` inclua 8064×6048.
- Distância mínima de foco da lente principal: ~15–20 cm conforme o modelo (VERIFICAR medindo). A face mais próxima da lente precisa ficar mais longe que isso.
- Sem zoom digital, sem flash.

### 14.2 Configuração

```swift
import AVFoundation

final class CameraCabine: NSObject {
    let sessao = AVCaptureSession()
    let saidaFoto = AVCapturePhotoOutput()
    let saidaVideo = AVCaptureVideoDataOutput()   // estabilidade e qualidade local
    private(set) var camera: AVCaptureDevice!

    func configurar(perfil: PerfilCamera) throws {
        guard let camera = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back)
        else { throw ErroCabine.semCamera }
        self.camera = camera

        sessao.beginConfiguration()
        defer { sessao.commitConfiguration() }
        sessao.sessionPreset = .photo
        let entrada = try AVCaptureDeviceInput(device: camera)
        guard sessao.canAddInput(entrada), sessao.canAddOutput(saidaFoto), sessao.canAddOutput(saidaVideo)
        else { throw ErroCabine.configuracao }
        sessao.addInput(entrada)
        sessao.addOutput(saidaFoto)
        sessao.addOutput(saidaVideo)

        try camera.lockForConfiguration()
        defer { camera.unlockForConfiguration() }
        if let formato = camera.formats.last(where: { f in
            f.supportedMaxPhotoDimensions.contains { $0.width == 8064 && $0.height == 6048 }
        }) {
            camera.activeFormat = formato
        }
        camera.isSubjectAreaChangeMonitoringEnabled = false
        let e = perfil.exposicao(.ambiente)                        // duração múltipla de 1/120 s
        camera.setExposureModeCustom(duration: CMTime(seconds: e.duracao, preferredTimescale: 1_000_000),
                                     iso: e.iso, completionHandler: nil)   // limitar ao minISO...maxISO do formato
        camera.setFocusModeLocked(lensPosition: perfil.foco(.deitado), completionHandler: nil)
        camera.setWhiteBalanceModeLocked(with: perfil.ganhosWB, completionHandler: nil) // limitar ao maxWhiteBalanceGain

        if let dims = camera.activeFormat.supportedMaxPhotoDimensions.max(by: { $0.width < $1.width }) {
            saidaFoto.maxPhotoDimensions = dims
        }
        saidaFoto.maxPhotoQualityPrioritization = .quality
        // Câmera apontada para baixo: a orientação do aparelho não é confiável. Fixar a rotação.
        saidaFoto.connection(with: .video)?.videoRotationAngle = 0    // iOS 17+; antes, videoOrientation
        saidaVideo.connection(with: .video)?.videoRotationAngle = 0
    }
}
```

### 14.3 Calibração (assistente no app)

1. **Berço vazio + folha de marcadores:** exposição automática por 2 s; ler `exposureDuration` e `iso`; converter para duração fixa de 1/60 s mantendo o brilho (`iso_novo = iso_auto × duração_auto ÷ (1/60)`), limitado ao `minISO...maxISO` do formato. Guardar como exposição `ambiente`.
2. **Balanço de branco:** ler `deviceWhiteBalanceGains` com a luz ambiente e travar esses ganhos.
3. **Foco por pose:** com um aparelho em cada pose (só `deitado` se D3 = espelhos), apontar `focusPointOfInterest` para o centro da face, `focusMode = .autoFocus`, esperar `isAdjustingFocus == false`, ler `lensPosition`. Com espelhos, conferir também a nitidez das bordas refletidas e, se precisar, usar um valor intermediário.
4. **Exposição da rasante:** foto rasante de um aparelho com risco conhecido; ajustar o ISO até que < 0,5% dos pixels do aparelho fiquem saturados. Repetir para `contraluz`, se houver.
5. **Geometria do berço:** px/mm pelos ArUco, orientação do aparelho por pose, região do berço e regiões dos espelhos.
6. **Referência do berço vazio:** guardar uma imagem pequena do berço vazio (usada para detectar mão na cena).
7. Salvar o `PerfilCamera` (seção 7.11) com versão incrementada.

### 14.4 Captura de um passo

Para cada luz do passo, na ordem `ambiente` → `rasante_a` → `rasante_b` → `contraluz`:

1. `POST /luz` no ESP32 e esperar o `200` com o estado pedido. Sem resposta em 1 s: tentar de novo; na terceira falha, avisar o técnico e pausar.
2. Se a exposição dessa luz for diferente da anterior, chamar `setExposureModeCustom` e **esperar o completion handler**, que informa o primeiro quadro com os novos valores.
3. Esperar mais 2 quadros (~70 ms).
4. Capturar:

   ```swift
   let ajustes = AVCapturePhotoSettings(format: [AVVideoCodecKey: AVVideoCodecType.hevc])
   ajustes.maxPhotoDimensions = saidaFoto.maxPhotoDimensions
   ajustes.photoQualityPrioritization = .speed      // menos fusão de quadros (VERIFICAR na fase 2)
   ajustes.flashMode = .off
   if let tipo = ajustes.availablePreviewPhotoPixelFormatTypes.first {
       ajustes.previewPhotoFormat = [kCVPixelBufferPixelFormatTypeKey as String: tipo,
                                     kCVPixelBufferWidthKey as String: 1024,
                                     kCVPixelBufferHeightKey as String: 768]
   }
   saidaFoto.capturePhoto(with: ajustes, delegate: delegado)
   ```

   Guarde uma referência forte ao delegado até a captura terminar (o exemplo AVCam da Apple faz isso).
5. No delegado: `fileDataRepresentation()` → gravar na pasta da fila + JSON de metadados (seção 7.3); rodar a qualidade local no `previewPixelBuffer` (pequeno e rápido).
6. Ao fim do passo: `POST /desligar` no ESP32.

Comparar na fase 2: `.speed` × `.balanced`, e HEIC × RAW Bayer ou ProRAW (se disponível), olhando microrriscos nas mesmas condições. Escolher pelo resultado, não pela teoria.

### 14.5 Máquina de estados do roteiro

```
naoPareado → pareado → calibrado → aguardandoQR
aguardandoQR      → (QR lido, exposição automática) → abrindoSessao (GET /cabine)
abrindoSessao     → apagandoTela (POST /tela; confirma vendo a tela escurecer; até 5 s)
para cada passo:
  posicionar      → aguardandoEstabilidade → capturando(luz) → verificando
  verificando     → ok: próxima luz ou próximo passo
                  → falhou: repetirPasso (até 3 vezes; depois pede ajuda ao técnico)
concluindo (POST /concluir) → aguardandoSugestao → resultado → aguardandoQR

Estados de erro (voltam ao ponto em que pararam):
  semRede            continua capturando; a fila envia depois
  luzSemResposta     pausa e pede para conferir o ESP32
  cameraInterrompida pausa (AVCaptureSession.wasInterruptedNotification) e retoma
  temperaturaAlta    reduz a análise de quadros; em .critical, pausa e avisa
```

O QR é lido **com exposição automática** (tela acesa e brilhante); só depois o perfil travado é aplicado.

### 14.6 Estabilidade e qualidade local

**Estabilidade** (antes de capturar):
- `AVCaptureVideoDataOutput` em `kCVPixelFormatType_420YpCbCr8BiPlanarFullRange`; usar só o plano Y; reduzir para ~320×240 com vImage; analisar 1 quadro a cada 2, numa fila serial.
- Diferença absoluta média entre quadros consecutivos abaixo de `T_mov` (ponto de partida: 1,5 nível de cinza) por 500 ms seguidos.
- Aparelho presente: `VNDetectRectanglesRequest` com a faixa de proporção esperada para a face (± 10%), dentro da região do berço do perfil. Para faixas finas, VERIFICAR se o Vision detecta; senão, usar limiar de brilho na região esperada.
- Sem mão na cena: a área do berço fora do aparelho igual à referência do berço vazio, dentro de `T_mao`.

**Qualidade local** (no preview de 1024 px de cada foto):

| Verificação | Regra (pontos de partida; calibrar na fase 2) |
|---|---|
| Nitidez | variância do Laplaciano dentro do aparelho ≥ `T_nitidez` |
| Estouro | pixels ≥ 250 dentro do aparelho: ≤ 0,5% na `ambiente`, ≤ 2% na rasante |
| Contorno | retângulo encontrado, proporção dentro de ± 10% da esperada |
| Tela apagada (passo da frente) | luminância média da região da tela abaixo de `T_tela` |

Os limiares ficam como constantes em `QualidadeLocal.swift`, com comentário dizendo de onde veio cada valor.

### 14.7 Cuidados

- iPhone câmera sempre no carregador. Acompanhar `ProcessInfo.processInfo.thermalState`.
- Wi-Fi: cabine e ESP32 na mesma rede. Redes com isolamento de clientes bloqueiam mDNS e o acesso ao ESP32: o app aceita um IP fixo configurável.
- Gravar `rotacao_graus` nos metadados; o Python **ignora** o EXIF de orientação.
- Permissão de rede local: o iOS pede na primeira chamada ao ESP32; o assistente de calibração deve provocar esse pedido logo no início.

---

## 15. Referência: pipeline de visão

Os trechos de código são **esboços** para orientar; os limiares iniciais saem da fase 0 e ficam em `config.py`, nunca espalhados no código.

### 15.1 Leitura

- `io_imagem.py` lê HEIC (`pillow-heif`), DNG (`rawpy`) e JPEG; **ignora EXIF de orientação**; devolve `float32` de 0 a 1.
- Detecção em tons de cinza (luminância; no RAW, o canal verde). A cor fica para o painel e para o PatchCore.

### 15.2 Qualidade (no servidor)

Repete as verificações da seção 14.6 em resolução total, só dentro do aparelho. Motivos de reprovação (texto fixo, aparece no painel e na cabine): `tremida`, `estourada`, `contorno não encontrado`, `orientação errada`, `aparelho fora do quadro`, `tela acesa`. Foto reprovada gera evento `foto_reprovada`.

### 15.3 Geometria e retificação

1. **Máscara do aparelho:**
   - com `contraluz`: limiar de Otsu (aparelho escuro sobre fundo claro) → silhueta limpa;
   - sem `contraluz`: limiar adaptativo + morfologia na foto `ambiente`, reforçados pela rasante (a moldura brilha na luz rasante);
   - plano B: RF-DETR-Seg pré-treinado no COCO (classe "cell phone").
2. Maior contorno → `cv2.minAreaRect` como chute inicial.
3. **Cantos precisos:** para cada lado, pegar os pontos do contorno a mais de 1,5 × o raio do canto (em px) dos cantos do chute e ajustar uma reta com `cv2.fitLine(..., cv2.DIST_HUBER, ...)`. A interseção das 4 retas dá 4 cantos virtuais com precisão subpixel. Os cantos arredondados não atrapalham porque ficam de fora do ajuste.
4. **Orientação:** pelo batente e por `perfil.orientacao`. Na traseira, conferir que a ilha de câmeras está perto da origem do referencial (seção 7.2); se estiver no canto oposto, girar 180°; se nada bater, `orientacao_ok = false`.
5. **Homografia:** `H = cv2.getPerspectiveTransform(cantos_px, cantos_mm * R)` e `cv2.warpPerspective(img, H, (round(W*R), round(Alt*R)), flags=cv2.INTER_LANCZOS4)`. A correspondência dos cantos segue o referencial da seção 7.2.
6. **Espelhos (se D3 = espelhos):** cada região de espelho do perfil mostra uma borda. A mesma técnica (retas e cantos) acha a borda; a homografia já desfaz o espelhamento, desde que a correspondência dos cantos respeite o referencial da seção 7.2.
7. **Conferências:**
   - resíduo dos pontos das bordas em relação às retas > 0,3 mm → sinalizar (moldura torta, contorno ruim ou distorção);
   - px/mm do aparelho × px/mm dos ArUco, corrigido pela diferença de altura → divergência > 2% indica contorno ruim.
8. Alinhamento entre luzes: as fotos de um passo devem coincidir. Conferir com correlação de fase (`cv2.phaseCorrelate`) entre `ambiente` e cada rasante; deslocamento > 2 px → corrigir pela homografia de cada foto (cada foto tem a sua) e registrar.

### 15.4 Camada (a): riscos na luz rasante

Ideia: na luz rasante, risco é uma linha fina e clara sobre fundo escuro. Subtrair a foto `ambiente` remove reflexos fixos.

1. Trabalhar na resolução nativa, só dentro da máscara da zona avaliada (tela ou vidro traseiro), excluindo uma faixa de 0,5 mm na borda.
2. `d = rasante − ambiente`, **sem cortar os negativos em 0**: com metade dos valores zerados, a mediana e o MAD do passo 5 viram zero e o limiar deixa passar quase a imagem toda.
3. **Top-hat** com elemento maior que a largura máxima de um risco → realça estruturas finas e claras e tira o fundo.
4. Opcional, se o top-hat gerar falsos positivos em texturas: filtro de cristas (Frangi do scikit-image, ou Hessiana com OpenCV em `float32`, que é mais rápida em ~5 MP).
5. **Limiar robusto:** mediana + k × MAD dentro da zona.
6. **Emendar** fragmentos (fechamento morfológico de ~1 mm), separar componentes conectados.
7. **Esqueleto** de cada componente → caminho mais longo → comprimento medido numa polilinha amostrada a cada 5 px; largura média aparente = área ÷ comprimento. Não some passos de 1 e √2 pixel a pixel: isso superestima o comprimento em ~5% em média (até 8% a 22,5°).
8. **Filtros:** comprimento ≥ 0,5 mm; alongamento (comprimento ÷ largura) ≥ 4, o que rejeita poeira e pontos.
9. Repetir em `rasante_a` e `rasante_b`; a fusão (15.8) junta as duas.

```python
from collections import deque

import cv2
import numpy as np
from skimage.morphology import skeletonize

def realcar(rasante, ambiente, mascara, px_mm, largura_max_mm=0.4):
    d = (rasante - ambiente).astype(np.float32)   # sem np.clip: o top-hat já tira o fundo
    k = int(round(largura_max_mm * px_mm * 4)) | 1
    el = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    th = cv2.morphologyEx(d, cv2.MORPH_TOPHAT, el)
    th[~mascara] = 0
    return th

def binarizar(th, mascara, k_mad=8.0):
    v = th[mascara]
    med = np.median(v)
    mad = np.median(np.abs(v - med)) * 1.4826 + 1e-9
    return (th > med + k_mad * mad) & mascara

def comprimento_esqueleto(esq, passo=5):
    """Comprimento (px) do caminho mais longo do esqueleto, medido numa polilinha
    amostrada a cada `passo` pixels. Em riscos ramificados, mede só o ramo mais longo."""
    ys, xs = np.nonzero(esq)
    if len(ys) < 2:
        return 0.0
    pixels = set(zip(ys.tolist(), xs.tolist()))
    vizinhos = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def mais_distante(origem):
        pai = {origem: None}
        fila = deque([origem])
        ultimo = origem
        while fila:
            p = fila.popleft()
            ultimo = p
            for dy, dx in vizinhos:
                q = (p[0] + dy, p[1] + dx)
                if q in pixels and q not in pai:
                    pai[q] = p
                    fila.append(q)
        return ultimo, pai

    ponta, _ = mais_distante(next(iter(pixels)))   # duas buscas: as duas pontas mais distantes
    outra, pai = mais_distante(ponta)
    caminho = []
    while outra is not None:
        caminho.append(outra)
        outra = pai[outra]
    amostra = caminho[::passo]
    if (len(caminho) - 1) % passo:
        amostra.append(caminho[-1])
    pts = np.array(amostra, dtype=float)
    return float(np.sum(np.hypot(*np.diff(pts, axis=0).T)))

def riscos(binario, px_mm, emenda_mm=1.0, comp_min_mm=0.5, alongamento_min=4.0):
    r = int(round(emenda_mm * px_mm)) | 1
    b = cv2.morphologyEx(binario.astype(np.uint8), cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r)))
    n, rot, stats, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    achados = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        esq = skeletonize(rot[y:y + h, x:x + w] == i)
        comp_mm = comprimento_esqueleto(esq) / px_mm
        if comp_mm < comp_min_mm:
            continue
        largura_mm = area / max(int(esq.sum()), 1) / px_mm
        if comp_mm / max(largura_mm, 1e-6) < alongamento_min:
            continue  # ponto ou poeira
        achados.append({"caixa_px": [int(x), int(y), int(w), int(h)],
                        "comprimento_mm": round(comp_mm, 2), "esqueleto": esq})
    return achados
```

A largura medida não serve para o critério: microrriscos são mais finos que um pixel e aparecem "largos" porque espalham luz. Use só o comprimento.

### 15.5 Visibilidade (`visivel` × `so_rasante`)

- Para cada risco, medir na foto `ambiente` a resposta do top-hat ao longo do esqueleto (dilatado 1 px): `contraste_ambiente`.
- `visivel` se `contraste_ambiente ≥ T_visivel`. Calibrar `T_visivel` com as marcações "visível a olho nu" dos técnicos (fase 1 e uso real), por regressão logística em `contraste_ambiente` e `comprimento_mm`.
- Até calibrar: usar o limiar da fase 0 e reduzir a `confianca` dos riscos perto do limiar (margem baixa → nunca automático).

### 15.6 Camada (b): anomalia com PatchCore

- **Onde:** traseira e moldura (bordas). A tela fica com as camadas (a) e (c).
- **Famílias de acabamento** (definidas em `dimensoes.py` por modelo e cor): por exemplo `vidro_brilhante_escuro`, `vidro_brilhante_claro`, `vidro_fosco_escuro`, `vidro_fosco_claro`, `aluminio_escuro`, `aluminio_claro`, `aco`, `titanio`. Um modelo PatchCore por família e por tipo de face (traseira, borda).
- **Dados:** faces retificadas de aparelhos com nota final A dada pelo técnico, cortadas em blocos de 256×256 px com 64 px de sobreposição, excluindo `lente_camera` (reflexos fortes).
- **Treino** (anomalib 2.x; VERIFICAR a API da versão instalada):

  ```python
  from anomalib.data import Folder
  from anomalib.engine import Engine
  from anomalib.models import Patchcore

  dados = Folder(name="traseira-vidro_fosco_escuro",
                 root="dados/patchcore/traseira-vidro_fosco_escuro",
                 normal_dir="normal", abnormal_dir="defeito")   # "defeito" só para validar
  modelo = Patchcore(backbone="wide_resnet50_2", layers=["layer2", "layer3"],
                     coreset_sampling_ratio=0.1)
  Engine().fit(model=modelo, datamodule=dados)
  ```

- **Limiar:** percentil 99,5 das notas de anomalia em blocos normais separados para validação.
- **Saída:** regiões do mapa acima do limiar → componentes → defeito `anomalia` com área e maior dimensão, sempre com revisão do técnico (R22). Se o detector (c) classificar a mesma região, o tipo do detector vence.

### 15.7 Camada (c): detector de defeitos

- **Modelo:** RF-DETR (Apache-2.0), tamanho S ou M para detecção, ou Seg se for preciso o contorno do defeito. Não use os tamanhos XL e 2XL de detecção nem a extensão `rfdetr_plus` (outra licença; seção 18).
- **Entrada:** blocos da face retificada (ex.: 640×640 px a R px/mm, 20% de sobreposição). Defeitos são pequenos demais para a imagem inteira reduzida.
- **Classes:** `risco`, `trinca`, `lascado`, `amassado`, `descascado`, `desgaste`, `mancha`.
- **Treino** (VERIFICAR nomes e parâmetros na versão instalada; formato COCO, com `train/`, `valid/` e `test/`):

  ```python
  from rfdetr import RFDETRSmall

  modelo = RFDETRSmall()
  modelo.train(dataset_dir="dados/coco/defeitos-v1", epochs=60, batch_size=4,
               grad_accum_steps=4, lr=1e-4, output_dir="modelos/rfdetr-s-defeitos-v1")
  ```

- Juntar detecções de blocos vizinhos por supressão de não máximos no espaço em mm.
- Trinca é o erro mais caro (nota D): limiar mais baixo para `trinca` (privilegiar recall) e confiança intermediária = revisão humana obrigatória.

### 15.8 Fusão por face

- Juntar as detecções de todas as fotos da mesma face (todas as luzes; com espelhos, as bordas aparecem nos dois passos).
- **Mesmo defeito se:** riscos — distância de Hausdorff entre as polilinhas ≤ 1,0 mm, ou sobreposição ≥ 50% do mais curto; demais — IoU das caixas ≥ 0,3, ou o centro de uma dentro da outra.
- **Defeito fundido:** geometria da detecção de maior contraste; `comprimento_mm` = o maior; `visibilidade` pela seção 15.5; tipo por prioridade detector > OpenCV > PatchCore (`anomalia`); `confianca` = a maior; `fotos` = todas onde apareceu.

### 15.9 Medição e zonas

- Zona do defeito = a zona com maior sobreposição. Em empate, a prioridade é `lente_camera` > `ilha_camera` > `recorte_tela` > `botao` > `porta` > `quina` > `tela`, `vidro_traseiro` ou `moldura`.
- A faixa de 0,5 mm na borda da frente e da traseira conta como `moldura`; quadrados de lado igual ao raio do canto nos 4 cantos de cada face (limitados à face) contam como `quina`.
- Medidas: risco → comprimento do esqueleto; demais → `maior_dimensao_mm` (maior lado do retângulo mínimo girado do contorno) e `area_mm2`.

### 15.10 Imagens para o painel e o laudo

- `retificada`: JPEG qualidade 90, a R px/mm, uma por foto.
- `anotada`: a retificada com os defeitos desenhados (cor fixa por tipo, igual à do painel) e as medidas em mm.
- Mapa de anomalia como camada semitransparente, quando houver.

### 15.11 Orçamento de tempo

| Etapa (por foto) | Alvo |
|---|---|
| Ler HEIC de 48 MP | ≤ 0,8 s |
| Qualidade + geometria + retificação | ≤ 1,0 s |
| Camada (a) numa região de ~5 MP | ≤ 1,5 s (CPU) |
| Camada (c) em blocos | ≤ 2 s com GPU ou MPS; em CPU pode passar de 10 s (D6) |
| Camada (b) em blocos | ≤ 2 s com GPU ou MPS |
| Fusão (por sessão) | ≤ 1 s |

As tarefas `foto` rodam durante a captura, então só o último passo e a fusão contam para os 10 s.

---

## 16. Referência: motor de critério

### 16.1 Princípios

- `avaliar(defeitos, modelo, criterio) → ResultadoNota` é uma **função pura**: sem banco, sem rede, sem relógio.
- As regras ficam em YAML versionado (`criterios/criterio-v1.yaml`, lido com PyYAML), validado por um esquema (Pydantic) que recusa chaves desconhecidas e valores fora dos enums.
- O resultado traz notas por face, nota final, justificativas legíveis, regras "a definir" acionadas e margens.
- Mudou uma regra = nova versão do critério (`criterio-v2`), nunca edição silenciosa da v1.

### 16.2 `criterio-v1.yaml` (rascunho a partir do PRD §10)

```yaml
versao: criterio-v1
fonte: docs/nota-estetica-criterio.md
notas: [A, B, C, D]                          # da melhor para a pior

grupos:                                       # zona → grupo de regras
  tela:     [tela, recorte_tela]
  traseira: [vidro_traseiro, ilha_camera, lente_camera]
  moldura:  [moldura, quina, botao, porta]

regras:                                       # por grupo, da pior nota para a melhor; vale a primeira que casar
  tela:
    padrao: A
    lista:
      - {nota: D, tipos: [trinca], motivo: "Trinca na tela"}
      - {nota: D, tipos: [lascado], maior_dimensao_mm_acima: 2, motivo: "Lascado no vidro maior que 2 mm"}
      - {nota: C, tipos: [lascado], motivo: "Lascado no vidro até 2 mm", a_definir: true}
      - {nota: C, tipos: [mancha, descascado], motivo: "Mancha ou descascado", a_definir: true}
      - {nota: C, tipos: [risco], visibilidade: visivel, motivo: "Risco visível"}
      - {nota: C, tipos: [risco], quantidade_acima: 5, motivo: "Mais de 5 riscos"}
      - {nota: C, tipos: [risco], comprimento_mm_acima: 15, motivo: "Risco maior que 15 mm"}
      - {nota: B, tipos: [risco], quantidade_acima: 2, motivo: "De 3 a 5 riscos só rasante"}
      - {nota: B, tipos: [risco], comprimento_mm_acima: 5, motivo: "Risco só rasante entre 5 e 15 mm"}
  traseira:
    padrao: A
    lista:
      - {nota: D, tipos: [trinca], motivo: "Vidro traseiro ou lente trincados"}
      - {nota: D, tipos: [lascado], maior_dimensao_mm_acima: 2, motivo: "Lascado maior que 2 mm", a_definir: true}
      - {nota: C, tipos: [lascado], motivo: "Lascado até 2 mm", a_definir: true}
      - {nota: C, tipos: [risco], visibilidade: visivel, motivo: "Risco visível"}
      - {nota: B, tipos: [risco], motivo: "Riscos leves só rasante", a_definir: true}
  moldura:
    padrao: A
    lista:
      - {nota: D, tipos: [amassado], maior_dimensao_mm_acima: 3, motivo: "Amassado maior que 3 mm"}
      - {nota: C, tipos: [amassado], motivo: "Amassado até 3 mm"}
      - {nota: C, tipos: [lascado, descascado], motivo: "Lascado ou descascado de pintura"}
      - {nota: C, tipos: [desgaste], motivo: "Desgaste nas quinas"}
      - {nota: C, tipos: [risco], maior_dimensao_mm_acima: 3, motivo: "Marca maior que 3 mm", a_definir: true}
      - {nota: B, tipos: [risco], maior_dimensao_mm_acima: 1, motivo: "Marcas leves até 3 mm"}
      - {nota: B, tipos: [risco], quantidade_acima: 2, motivo: "Mais de 2 marcas até 1 mm"}

gerais:
  nota_final: pior_face
  no_minimo:                                  # a face fica com esta nota ou pior
    - {nota: D, tipos: [trinca], zonas: [tela, vidro_traseiro, lente_camera], motivo: "Trinca em vidro"}
    - {nota: C, tipos: [risco], zonas: [lente_camera], motivo: "Risco sobre a lente da câmera"}

anomalia:                                     # defeitos sem classe (R22)
  tratar_como: risco                          # a definir na fase 1
  exige_revisao: true
```

### 16.3 Semântica

1. **Entrada:** defeitos com `estado` ≠ `rejeitado` (na sugestão, todas as propostas; na avaliação final, confirmados + desenhados pelo técnico).
2. **Por face e por grupo:** pegar os defeitos da face cujas zonas pertencem ao grupo. Percorrer `lista` na ordem. Uma regra **casa** se houver ao menos um defeito que passe nos filtros (`tipos`, `zonas`, `visibilidade`) e, se a regra tiver predicado numérico:
   - `quantidade_acima: n` → quantidade de defeitos filtrados > n;
   - `comprimento_mm_acima: x` → algum com `comprimento_mm` > x;
   - `maior_dimensao_mm_acima: x` → algum com `maior_dimensao_mm` > x;
   - `area_mm2_acima: x` → algum com `area_mm2` > x.

   Nota do grupo = nota da primeira regra que casar, ou `padrao`.
3. **Nota da face** = pior nota entre os grupos; depois aplicar `gerais.no_minimo` (a face fica com aquela nota ou pior). Face sem defeitos = A.
4. **Nota final** = pior face.
5. **Justificativas:** motivo + números ("3 riscos só rasante, maior 9,8 mm → B").
6. **Margens:** para cada predicado numérico das regras do grupo, a distância relativa entre o valor observado e o limite (`|valor − limite| ÷ limite`). A margem do resultado é a menor delas. Margem < 10% impede a nota automática (seção 13.3).
7. Regra com `a_definir: true` acionada → o resultado leva `pendencias` e nunca vira nota automática.

### 16.4 Lacunas do PRD §10 (levar à fase 1)

| # | Lacuna | Proposta |
|---|---|---|
| L1 | Lascado ≤ 2 mm na tela não tem nota | C |
| L2 | Traseira: "A = sem marcas visíveis" permite marcas só rasante? Quantas e de que tamanho são "riscos leves" (B)? | mesmos limites da tela |
| L3 | Lascado no vidro traseiro não aparece | igual à tela |
| L4 | Moldura A: "sem marcas visíveis" e "até 2 marcas ≤ 1 mm" — essas marcas podem ser visíveis? | sim |
| L5 | Moldura: marca > 3 mm sem amassado não tem nota | C |
| L6 | "Moldura torta": como medir | o técnico marca; a visão só sinaliza resíduo de reta > 0,3 mm |
| L7 | Mancha e descascado na tela e na traseira | C |
| L8 | Defeito `anomalia` (sem classe) | mesma regra de risco do mesmo tamanho + revisão obrigatória |
| L9 | Botões e porta | grupo moldura |
| L10 | "Mais de 5 riscos" conta por face ou no aparelho inteiro | por face |

### 16.5 Testes do motor

- Cada exemplo resolvido do documento do critério vira um caso de teste parametrizado.
- Propriedades (com `hypothesis`, como dependência de teste se o backend ainda não usar): acrescentar um defeito nunca melhora a nota; retirar um defeito nunca piora; a ordem dos defeitos não muda o resultado; mesma entrada → mesma saída.
- Validação do YAML: enums válidos; dentro de cada grupo, as regras estão em ordem da pior nota para a melhor.

---

## 17. Testes e verificação

### 17.1 Testes automáticos

| Componente | O que testar |
|---|---|
| `visao` | **sintéticos** (`ferramentas/sintetico.py`): retângulo escuro com ruído, riscos de comprimento conhecido (erro ≤ 5% ou ≤ 0,5 mm), poeira em pontos (≥ 95% rejeitada), digital difusa; **geometria**: retângulo de cantos arredondados deformado por homografia aleatória (erro de canto < 0,2 mm, escala < 0,5%); **regressão**: resultados das fotos da fase 0 guardados e comparados |
| Motor de critério | seção 16.5 |
| Backend | rotas, validação, idempotência (mesma chave = uma foto), escopo por loja, amostra cega (sugestão escondida), gate (recusa `automatico` sem relatório), fila com reservas concorrentes, migração sobe e desce |
| App iOS | XCTest da máquina de estados e do detector de estabilidade, com sequências de quadros gravadas |
| Painel | testes de componente no padrão do painel |

### 17.2 Checklist no aparelho (cabine)

- [ ] Permissões de câmera e rede local concedidas.
- [ ] Fotos de 8064×6048 de fato.
- [ ] ISO, exposição, foco e balanço de branco idênticos entre fotos da mesma luz e pose (conferir metadados).
- [ ] Nenhuma foto "meio acesa": a luz troca antes do disparo.
- [ ] Sem faixas horizontais (flicker) com as lâmpadas da loja.
- [ ] QR lido com a tela do aparelho avaliado acesa.
- [ ] Tela do aparelho avaliado preta em ≤ 2 s (testar um modelo LCD também).
- [ ] Wi-Fi desligado no meio da captura: fotos ficam na fila e sobem quando volta.
- [ ] App para segundo plano e volta: o roteiro retoma.
- [ ] 30 aparelhos seguidos sem superaquecer.
- [ ] Tempo total por aparelho medido (meta ≤ 60 s).

### 17.3 Simulação ponta a ponta

`visao/ferramentas/simular_cabine.py` faz o papel da cabine contra o backend local: cria uma sessão de teste (pelo mecanismo de teste que o backend já tiver), envia as fotos da fase 0 seguindo o roteiro, chama `concluir`, espera a sugestão e confere o retorno das rotas do painel. Roda com o worker nulo (fase 3) e com o worker real (fase 4).

---

## 18. Licenças, bases e modelos

Não é parecer jurídico. Na dúvida, o responsável consulta o jurídico. VERIFICAR a licença de cada item na data de uso.

### 18.1 Bibliotecas e modelos

| Item | Licença | Situação |
|---|---|---|
| OpenCV (4.5 ou mais novo) | Apache-2.0 | ok |
| scikit-image | BSD-3-Clause | ok |
| NumPy, PyTorch, torchvision | BSD | ok |
| anomalib | Apache-2.0 | ok |
| RF-DETR (`rfdetr`): detecção N, S, M, L e segmentação | Apache-2.0 | **padrão** para o detector (R15) |
| RF-DETR XL e 2XL de detecção, extensão `rfdetr_plus` | licença de plataforma da Roboflow (não Apache) | não usar |
| Ultralytics YOLO11 e YOLO26 | AGPL-3.0, ou licença Enterprise paga | só com decisão D7 e licença comprada; a Ultralytics diz que a Enterprise é o caminho para uso comercial, inclusive em ferramentas internas |
| pillow-heif, rawpy | BSD-3-Clause e MIT (embutem bibliotecas LGPL) | ok no servidor, sem distribuição |
| Firmware ESP32 (Arduino-ESP32, PlatformIO) | LGPL / Apache-2.0 | ok para uso interno; VERIFICAR antes de distribuir |

### 18.2 Bases públicas (pesquisa do PRD, 2026-10-13)

| Base | Licença | Situação | Classes → nossas |
|---|---|---|---|
| Mobile Damage Diagnosis | CC BY 4.0 | usar no pré-treino, com atribuição | crack → `trinca`; scratch → `risco`; dent → `amassado`; dead pixel → descartar |
| Mobile phone defects 3 | conferir na página | só depois de conferir | scratch → `risco`; stain → `mancha`; oil → descartar |
| Smartphone crack | CC BY 4.0 | usar com atribuição | crack → `trinca` |
| Glass defect detection, Crackedscreen, Scratches-and-dents-detection | conferir na página | só depois de conferir | chipping → `lascado`; broken, shatter → `trinca`; bubble, dislocation → descartar |
| MSD | GPL-3.0 | **não usar** (efeito sobre pesos de modelo comercial é incerto; o PRD dizia "confirmar") | — |
| SSGD, MVTec AD, CarDD, AI4Manufacturing 188 | não comerciais | **não usar** | — |

### 18.3 Como registrar

`visao/DATASETS.md`, uma seção por base:

```markdown
## Mobile Damage Diagnosis
- URL: https://universe.roboflow.com/abhinavpoc/mobile-damage-diagnosis
- Versão: N · baixada em AAAA-MM-DD
- Licença: CC BY 4.0 (conferida na página em AAAA-MM-DD)
- Atribuição: <texto pedido pela página>
- Imagens: 1.901 · Classes: crack→trinca, scratch→risco, dent→amassado, dead pixel→descartada
- Uso: pré-treino do detector (rfdetr-s-base-v1)
```

`visao/MODELOS.md`, uma seção por modelo: versão, hash SHA-256 dos pesos, código usado (commit), bases e versões, parâmetros de treino, métricas (no holdout próprio), data e onde está guardado.

---

## 19. Riscos conhecidos

| Risco | Sinal | Mitigação |
|---|---|---|
| Luz rasante numa só direção esconde riscos | risco visto em `ra` e não em `rb` na fase 0 | R1 |
| Faces fora de foco | nitidez baixa em laterais, topo ou base | R2, R3; espelhos ou presets por pose |
| Poeira e digital viram "risco" | muitos riscos curtos em aparelho limpo | limpeza obrigatória; filtro de alongamento; comparar as duas direções de luz |
| Película e capa | riscos demais em aparelho "bom" | retirar antes (processo e aviso na tela da cabine) |
| Aparelho preto em fundo preto | contorno falha | contraluz (D4); moldura realçada na rasante |
| Luz do dia variando | contraste da foto ambiente muda ao longo do dia | exposição travada; luz difusa de cima; anteparo maior; normalizar pela folha de calibração |
| Faixas por lâmpadas (rede de 60 Hz) | listras horizontais nas fotos | exposição múltipla de 1/120 s; PWM do ESP32 ≥ 20 kHz |
| Reflexo do ambiente e de pessoas no vidro | formas claras grandes; rosto refletido (LGPD) | anteparo preto; subtração ambiente × rasante; revisar imagens anotadas |
| LCD não fica preto | tela cinza na foto da frente | brilho 0 (R18) |
| Viés de automação | concordância alta nas sessões não cegas e baixa nas cegas | amostra cega (R11) |
| Vazamento entre treino e teste | métrica boa no teste e ruim no uso | separação por aparelho; holdout congelado |
| Técnicos discordam | kappa baixo na fase 1 | critério escrito e estudo antes de juntar dados |
| Bases públicas diferentes das nossas | detector pré-treinado acerta pouco | só pré-treino; base principal é a nossa |
| Licença do detector | — | RF-DETR (R15) |
| Armazenamento | espaço ou custo subindo | R2 + retenção (R12) |
| iPhone câmera esquentando | `thermalState` alto, quadros perdidos | carregador; reduzir análise; pausar |
| Wi-Fi com isolamento de clientes | ESP32 não responde | IP fixo configurável |
| Worker parado | sessões presas em `processando` | painel funciona sem sugestão; alerta se a fila passar de 5 min |

---

## Apêndice A — Dimensões e zonas por modelo

Fica em `backend/app/estetica/dimensoes.py`. A chave é o **identificador do modelo** (ProductType, ex.: `iPhone14,5`), que é o que a estação lê pelo cabo; não use o nome comercial como chave.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Retangulo:                 # mm, no referencial da face (seção 7.2)
    x: float
    y: float
    w: float
    h: float
    raio: float = 0.0

@dataclass(frozen=True)
class Modelo:
    identificadores: tuple[str, ...]          # ("iPhone14,5",)
    nome: str                                 # "iPhone 13"
    largura_mm: float
    altura_mm: float
    espessura_mm: float
    raio_canto_mm: float                      # a Apple não publica: medir
    tela: str                                 # "oled" ou "lcd"
    moldura: str                              # "aluminio", "aco" ou "titanio"
    traseira: str                             # "vidro_brilhante" ou "vidro_fosco"
    zonas: dict[str, dict[str, tuple[Retangulo, ...]]] = field(default_factory=dict)  # face → zona → retângulos
    fonte: str = ""                           # URLs + data da consulta
    verificado: bool = False                  # True só depois de conferir numa foto retificada

MODELOS = {
    "iPhone14,5": Modelo(
        identificadores=("iPhone14,5",),
        nome="iPhone 13",
        largura_mm=71.5, altura_mm=146.7, espessura_mm=7.65,   # valores do PRD; VERIFICAR na Apple
        raio_canto_mm=0.0,                                     # MEDIR
        tela="oled", moldura="aluminio", traseira="vidro_brilhante",   # VERIFICAR
        zonas={
            "frente":   {"recorte_tela": ()},                   # MEDIR (notch)
            "traseira": {"ilha_camera": (), "lente_camera": ()}, # MEDIR
            "lat_esq":  {"botao": ()},                           # volume e chave de silêncio: MEDIR
            "lat_dir":  {"botao": ()},                           # botão lateral: MEDIR
            "base":     {"porta": ()},                           # conector: MEDIR
        },
        fonte="https://support.apple.com/… (consultado em AAAA-MM-DD)",
    ),
}
```

A família de acabamento usada pelo PatchCore (seção 15.6) sai de `traseira`, `moldura` e da cor do aparelho (clara ou escura). Se a estação conseguir ler a cor pelo cabo (por exemplo, valores de cor do lockdown), use; senão, o técnico informa uma vez por modelo e cor (VERIFICAR o que o pymobiledevice3 expõe).

**Como preencher:**
1. Dimensões externas, tipo de tela e materiais: página de especificações técnicas de cada modelo no site de suporte da Apple. Registrar URL e data em `fonte`.
2. Posição de ilha de câmeras, lentes, botões, porta e recorte da tela: desenhos dimensionais das diretrizes de acessórios da Apple (Accessory Design Guidelines, em developer.apple.com/accessories; VERIFICAR disponibilidade). Se não houver, **medir numa foto retificada** de um aparelho nota A daquele modelo com `ferramentas/marcar_zonas.py` (o humano desenha os retângulos; a ferramenta salva em mm).
3. Raio de canto: ajustar um arco nos cantos do contorno de uma foto retificada.
4. Marcar `verificado=True` só depois de sobrepor as zonas numa foto real e conferir com o técnico.
5. Testes: todos os retângulos dentro da face; identificadores únicos; dimensões positivas.

**Ordem de cadastro:** pelos modelos de maior volume na loja. Cobrir, no mínimo, do iPhone XR/11 aos atuais, incluindo SE (2ª e 3ª geração), 16e e Air, e os lançamentos posteriores (VERIFICAR a linha atual da Apple). Modelo sem cadastro → `422` em `GET /cabine/{token}` (seção 7.3).

---

## Apêndice B — Prompts prontos para cada sessão

Cole no Claude Code, um por sessão. Ajuste os nomes de pasta se necessário.

**1. Preparação + fase 0 (código):**
> Leia docs/guia-claude-code-nota-estetica.md (seções 0 a 8) e docs/prd-nota-estetica.md. Primeiro me mostre a tabela de ajustes (seção 3) e as decisões pendentes (seção 4) para eu aceitar ou recusar, e registre minhas respostas em openspec/changes/nota-estetica-automatica/design.md. Depois prepare o pacote visao/ e os scripts da fase 0, gere a folha de marcadores e me passe o protocolo de fotos. Pare quando estiver pronto para receber as fotos.

**2. Fase 0 (análise):**
> As fotos da fase 0 estão em visao/prototipos/fotos/ e a anotação do técnico em anotacao.csv. Rode os protótipos da seção 8.3, gere docs/nota-estetica-fase0-relatorio.md com imagens e números e me traga as recomendações para D1 a D4.

**3. Fase 1 (critério):**
> Siga a seção 9 do guia. Redija docs/nota-estetica-criterio.md, o criterio-v1.yaml, o motor de critério com testes, o modelo de planilha do estudo e o script de concordância. Liste as lacunas da seção 16.4 com a sua proposta para cada uma.

**4. Fase 1 (resultado do estudo):**
> As planilhas dos dois técnicos estão em docs/estudo/. Rode a concordância, me mostre a matriz e as divergências e proponha ajustes no critério.

**5. Fase 2 (hardware e firmware):**
> Siga as seções 10.1 e 10.2, usando as decisões D1 a D4 registradas em design.md. Gere hardware/cabine-a/ (README, berco.scad, STL) e o firmware em hardware/cabine-luz/. Me dê o passo a passo de montagem e de gravação do ESP32.

**6. Fase 2 (app modo Cabine e tela QR + preto):**
> Siga as seções 10.3 e 10.4, com a referência da seção 14. Leia antes app-ios/ (project.yml, LeitorQR.swift, Envio.swift, Testes/Sujeira.swift). Implemente o modo Cabine e a tela QR + preto, compile, rode os testes de lógica e me passe o checklist da seção 17.2.

**7. Fase 3 (backend):**
> Siga a seção 11.1 e os contratos da seção 7. Explore backend/ primeiro e siga os padrões existentes. Crie migração, rotas, fila, eventos, armazenamento, amostra cega e o worker nulo, com testes. Não faça commit.

**8. Fase 3 (painel e laudo):**
> Siga as seções 11.2 a 11.4 com o guia visual morecheck-sistema e o padrão do painel: tela de avaliação com atalhos, relatório de concordância e bloco no laudo. Rode a simulação da seção 17.3 no fim.

**9. Fase 4 (visão):**
> Siga a seção 12 com a referência da seção 15. Comece pelo worker, qualidade, geometria e camada (a); rode a simulação ponta a ponta com as fotos da fase 0 e me traga o relatório de concordância. Não use Ultralytics (D7).

**10. Fase 4 (detector):**
> Siga as seções 12.3, 12.4 e 15.7: baixe só as bases permitidas na seção 18, registre as licenças em DATASETS.md, treine o RF-DETR de base e depois faça o ajuste fino com as marcações do painel, separando por aparelho.

**11. Fase 5:**
> Siga a seção 13: implemente o gate, o modo sombra, a automação seletiva e o monitoramento. Me mostre o relatório que diz se podemos ligar o automático em alguma loja.

**Retomar trabalho:**
> Leia o guia (seções 0 a 7), design.md, tasks.md e o último resumo de sessão. Diga em que ponto estamos e continue pela próxima tarefa pendente.

---

## Apêndice C — Glossário

| Termo | Significado |
|---|---|
| Luz rasante | luz quase paralela à superfície; faz riscos finos brilharem sobre fundo escuro |
| Contraluz | luz por baixo do aparelho; gera uma silhueta limpa para achar o contorno |
| Retificar | corrigir a perspectiva para que a face vire um retângulo em escala conhecida (px/mm) |
| Homografia | transformação que leva os 4 cantos da foto aos 4 cantos reais em mm |
| Top-hat | operação morfológica que realça estruturas claras menores que um tamanho dado |
| Frangi | filtro que realça estruturas em forma de linha (cristas) |
| Esqueleto | linha de 1 pixel no meio de um traço; usado para medir comprimento |
| MAD | desvio absoluto mediano; medida de dispersão que ignora valores extremos |
| PatchCore | método que aprende como é uma superfície perfeita e aponta o que foge dela |
| RF-DETR | detector de objetos (e segmentação) da Roboflow, licença Apache-2.0 |
| Kappa ponderado | concordância entre avaliadores descontando o acaso; erro de 2 notas pesa mais que erro de 1 |
| Amostra cega | sessões em que o técnico avalia sem ver a sugestão da máquina |
| Holdout | conjunto de teste congelado que nunca entra no treino |
| Lease | prazo em que uma tarefa reservada fica com um worker antes de voltar à fila |
| Idempotência | repetir o mesmo envio não cria duplicata |
| ArUco | marcador impresso que o OpenCV localiza com precisão; serve de referência de escala |
| mDNS | descoberta de aparelhos na rede local por nome (`*.local`) |
| PWM | controle de brilho ligando e desligando a luz muito rápido |
