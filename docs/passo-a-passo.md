# Passo a passo para finalizar e testar a nota estética

O código está pronto e testado no computador. O que falta é **físico** (fotos, cabine, iPhone),
**decisão** (D1 a D12, critério) e **integração** com o Morecheck real. Siga as etapas na ordem;
cada uma termina num "Pronto quando". O andamento oficial fica em
`openspec/changes/nota-estetica-automatica/tasks.md`.

| Etapa | O quê | Quem | Tempo |
|---|---|---|---|
| 1 | Conferir tudo no computador | você | 1 h |
| 2 | PRD e critério | você + Claude Code | 1 h |
| 3 | Fase 0: fotos e decisões D1–D4 | você + Claude Code | 1 dia |
| 4 | Fase 1: estudo com dois técnicos | técnicos + você | 1–2 dias |
| 5 | Integrar no Morecheck real | Claude Code + você | 2–4 dias |
| 6 | Montar a cabine e gravar o ESP32 | você | 1–2 dias (+ entrega das compras) |
| 7 | Instalar o app no iPhone e calibrar | você | meio dia |
| 8 | Piloto na loja (produção) | você + técnico | 1–2 semanas |
| 9 | Coleta de dados e treino dos modelos | Claude Code + você | semanas |
| 10 | Ligar o modo automático | você (decisão) | — |

As etapas 3 e 4 podem andar em paralelo. A etapa 6 pode começar logo depois da 3, porque as
decisões D1 a D4 definem o que comprar.

---

## Já configurado neste Mac (2026-10-16)

- `~/.morecheck/desenvolvimento.env` com os segredos de desenvolvimento (gerados aleatoriamente);
  backend e worker leem esse arquivo sozinhos.
- Banco `morecheck_dev` com uma loja, um técnico, um admin e uma cabine (tokens em `~/.morecheck/dev-tokens.json`).
- Scripts do dia a dia:

  ```bash
  scripts/subir_dev.sh          # backend + painel (http://127.0.0.1:8000/painel/) + worker
  scripts/simular_aparelho.sh   # um aparelho passando pela cabine (fotos sintéticas ou as suas)
  scripts/parar_dev.sh          # desliga
  scripts/testar_local.sh       # teste ponta a ponta isolado, desliga tudo no fim
  ```
- Painel conferido no navegador (fila, avaliação, concordância, cabines, como técnico e admin).
- App iOS testado no simulador (iOS 18.6): tela QR + preto e pareamento passam (`scripts/testar_simulador.sh`).
- Treino validado com dados sintéticos (`visao/ferramentas/teste_treino.py --rapido` e PatchCore):
  a cadeia funciona. Treinar de verdade neste Mac de 8 GB não é viável: usar um Mac M-series com
  mais memória ou GPU (decisão D6).
- Teste no iPhone de um colaborador: `docs/TESTE-IPHONE.md`.
- Commits locais feitos (sem push).

## Etapa 1 — Conferir tudo no computador (hoje, ~30 min)

1. **Rodar os testes** (Postgres precisa estar ligado):

   ```bash
   cd ~/morecheck
   (cd backend && uv run pytest -q)                       # esperado: 71 passed
   (cd visao && uv run pytest -q)                         # esperado: 44 passed
   (cd painel && npm install && npx vitest run)           # esperado: 10 passed
   (cd app-ios/Pacotes/CabineNucleo && swift test)        # esperado: 21 tests, 0 failures
   ```

2. **Teste ponta a ponta com fotos sintéticas** (sobe backend e worker, simula a cabine, desliga tudo):

   ```bash
   scripts/testar_local.sh
   ```
   _Esperado:_ `Sugestão: … "nota_final": "C"`, `Tempo após a última foto: < 10 s`, `5 defeitos` na frente e `OK` no fim.

3. **Usar o painel você mesmo:**

   ```bash
   scripts/subir_dev.sh && scripts/simular_aparelho.sh
   ```
   Abra http://127.0.0.1:8000/painel/, cole o token do técnico (impresso pelo `subir_dev.sh`) e confira:
   - [ ] a fila mostra o iPhone 13;
   - [ ] na sessão, a frente aparece retificada; roda do mouse dá zoom; botão **1:1** funciona;
   - [ ] **espaço** troca a camada (Ambiente, Rasante A, Rasante B) e os riscos aparecem em amarelo;
   - [ ] **X** rejeita o defeito selecionado e a "nota pela regra" muda;
   - [ ] **N** e arrastar desenha um risco novo, com a medida em mm;
   - [ ] dar nota diferente da regra pede justificativa; **Enter** salva;
   - [ ] aba **Concordância** abre; em **Cabines**, "Parear nova cabine" mostra um QR.

   Anote o que estiver estranho (layout, textos, lentidão) e peça os ajustes ao Claude Code.
   Para desligar: `scripts/parar_dev.sh`.

**Pronto quando:** testes verdes, `testar_local.sh` com `OK` e o painel conferido.

---

## Etapa 2 — PRD e critério (~1 h)

1. Copie o PRD para `docs/prd-nota-estetica.md`.
2. Peça ao Claude Code:
   > Compare docs/nota-estetica-criterio.md e o criterio-v1.yaml com o PRD §10 e me mostre as diferenças.
   > Corrija o que divergir e liste as lacunas L1–L10 que continuam abertas.
3. Leia o critério (`docs/nota-estetica-criterio.md`), principalmente as seções 4 (regras) e 8
   (exemplos). Ele vai para os técnicos na etapa 4.

**Pronto quando:** critério conferido contra o PRD.

---

## Etapa 3 — Fase 0: fotos e decisões D1–D4 (~1 dia)

Responde, com números, como deve ser a cabine **antes de comprar e imprimir**.

1. **Imprimir** `visao/prototipos/saida/marcadores.pdf` em 100%. Conferir com régua: quadrado = 30 mm.
2. **Separar** 3 a 5 aparelhos (1 quase perfeito, 1 com riscos finos, 1 com riscos visíveis, 1 com
   amassado na moldura, 1 trincado se houver; **pelo menos um preto**) e o material da lista em
   `visao/prototipos/PROTOCOLO.md`.
3. **Fotografar** seguindo o protocolo. Não pule as fotos de foco, espelho e **`espelho_frente_ra`**:
   ela mede se o espelho faz sombra na luz rasante (o risco que decide D3).
4. **Anotação do técnico:** `anotacao.csv` (modelo em `visao/prototipos/anotacao-modelo.csv`).
5. **Copiar** fotos e anotação para `visao/prototipos/fotos/` e conferir:

   ```bash
   cd ~/morecheck/visao
   uv run python -I prototipos/conferir_fotos.py           # deve terminar com "OK"
   prototipos/rodar_tudo.sh 250                            # 250 = altura real da lente até a mesa, em mm
   ```
   _Se o Mac tiver 8 GB:_ feche o navegador antes (fotos de 48 MP usam ~4 GB).
6. **Análise:** peça ao Claude Code (prompt 2 do Apêndice B do guia):
   > As fotos da fase 0 estão em visao/prototipos/fotos/. Revise docs/nota-estetica-fase0-relatorio.md,
   > as imagens em docs/img/fase0/ e me traga as recomendações para D1 a D4, incluindo a sombra dos espelhos.
7. **Decidir** D1 (luz), D2 (altura da câmera), D3 (espelhos ou suportes em pé), D4 (contraluz).
   O Claude Code registra em `design.md` e ajusta as configurações (`ESTETICA_ROTEIRO`, `ESTETICA_CONTRALUZ`…).

**Pronto quando:** relatório revisado e D1–D4 registradas.

---

## Etapa 4 — Fase 1: estudo de concordância (1–2 dias, pode ser junto com a 3)

Tudo preparado em `docs/estudo/` (instruções no `README.md` de lá).

1. **Separar 20 aparelhos**, com pelo menos 4 de cada nota (se faltar D, pelo menos 2), etiquetados
   A01 a A20, e preencher `docs/estudo/aparelhos.csv` (não mostrar aos técnicos).
2. **Dois técnicos**, cada um sozinho, avaliam os 20 usando `docs/nota-estetica-criterio.md` e
   preenchem `docs/estudo/tecnico1.csv` e `tecnico2.csv` (já montadas: 20 aparelhos × 6 faces + final).
   Um não pode ver a planilha do outro.
3. **Calcular:**

   ```bash
   cd ~/morecheck/visao
   uv run python -I ferramentas/concordancia.py ../docs/estudo/tecnico1.csv ../docs/estudo/tecnico2.csv \
     --saida ../docs/estudo/divergencias.csv
   ```
4. **Reunião** com os técnicos sobre cada divergência e cada lacuna L1–L10. O Claude Code reescreve as
   regras (prompt 4 do Apêndice B). Repita até atingir a meta.
5. **Aprovar** o `criterio-v1` e gravar o kappa obtido como linha de base do modo automático:
   `ESTETICA_KAPPA_TECNICOS=<kappa>` em `~/.morecheck/producao.env`.

**Pronto quando:** concordância exata ≥ 85% **e** kappa ≥ 0,80, critério aprovado.

---

## Etapa 5 — Integrar no Morecheck real (2–4 dias de Claude Code)

Backend, painel e app foram feitos como projetos separados, com **substitutos (STUBs)** para loja,
usuário, sessão, registro, autenticação e laudo.

1. Coloque o repositório real do Morecheck acessível nesta máquina (ou me diga o caminho/URL).
2. Peça ao Claude Code:
   > Integre a nota estética no repositório real do Morecheck: módulo backend/app/estetica (sem os stubs
   > de app/base e sem a migração 0001), o bloco do laudo no gerador de PDF, as telas do painel e
   > Sources/Cabine + Sources/Estetica no app. Siga os padrões existentes. Não faça commit.
3. Rode os testes do projeto real e o `testar_local.sh` adaptado.

**Pronto quando:** tudo compila e os testes passam dentro do Morecheck real.

---

## Etapa 6 — Montar a cabine e gravar o ESP32 (1–2 dias + entrega)

Guia completo: `hardware/cabine-a/README.md`.

1. **Comprar** a lista da seção 1 (ajustada pelas decisões D1–D4).
2. **Imprimir** `berco.stl`, `suporte_espelho.stl` (4×, se D3 = espelhos) e `suporte_led.stl` (4×),
   em PLA/PETG preto fosco. Se D2/D3 mudarem medidas, peça ao Claude Code para ajustar o `berco.scad`.
3. **Montar** e ligar a eletrônica (seção 4 do README; GND comum!).
4. **Gravar o ESP32** (a chave das luzes já está gerada em `~/.morecheck/desenvolvimento.env`):

   ```bash
   cd ~/morecheck/hardware/cabine-luz
   ./configurar.sh "<nome da rede Wi-Fi da loja>" 1     # pede a senha do Wi-Fi sem mostrar
   uvx --from platformio pio run -t upload               # com o ESP32 no USB
   uvx --from platformio pio device monitor              # deve mostrar o IP e "mDNS: morecheck-cabine-1.local"
   ```
5. **Testar as luzes** (troque `<chave>`):

   ```bash
   curl -s -X POST http://morecheck-cabine-1.local/luz -H 'X-Chave-Cabine: <chave>' \
     -H 'Content-Type: application/json' -d '{"a":100}'
   ```
   _Esperado:_ a barra `a` acende; depois de 2 minutos sem comando, apaga sozinha.

**Pronto quando:** as conferências da seção 5 do README passam.

---

## Etapa 7 — App no iPhone da cabine e calibração (meio dia)

1. **Assinatura:** a plataforma iOS já está instalada. Falta uma conta Apple Developer (time da
   empresa) para assinar o app e instalar no iPhone.
2. **Gerar e abrir o projeto:**

   ```bash
   cd ~/morecheck/app-ios && xcodegen generate && open Morecheck.xcodeproj
   ```
   Em Signing & Capabilities, escolha o time. Conecte o iPhone da cabine e rode (⌘R).
   (Depois da etapa 5, isso passa a ser o app real.)
3. **Parear:** no painel, Concordância → Cabines → **Parear nova cabine**. No iPhone: Modo Cabine →
   leia o QR ou digite o código. Permita câmera e rede local.
4. **Luzes:** no app, informe o endereço do ESP32 (ou o IP, se a rede bloquear `.local`) e a chave
   `CABINE_LUZ_CHAVE` de `~/.morecheck/desenvolvimento.env` (a mesma do `segredos.h`).
   Para o iPhone falar com o backend do Mac: `scripts/subir_dev.sh --rede` e use na API o endereço que ele mostrar.
5. **Calibrar:** siga os 6 passos do assistente (berço vazio, foco, rasante, marcadores, orientação do topo).
6. **Testar com 3 aparelhos** e marcar o checklist do guia (seção 17.2):
   - [ ] fotos de 8064×6048 (veja no painel, na foto original);
   - [ ] ISO, exposição, foco e balanço iguais entre fotos da mesma luz (metadados);
   - [ ] nenhuma foto "meio acesa" e sem faixas horizontais;
   - [ ] tela do aparelho avaliado fica preta em ≤ 2 s (testar um LCD também: SE, XR ou 11);
   - [ ] desligar o Wi-Fi no meio: as fotos ficam na fila e sobem quando volta;
   - [ ] 30 aparelhos seguidos sem esquentar;
   - [ ] tempo por aparelho ≤ 60 s (mediana de 10, com o técnico real).
7. Se algo reprovar foto boa ou aceitar foto ruim, peça ao Claude Code para recalibrar os limiares
   (nitidez, movimento, mão) com os casos reais.

**Pronto quando:** checklist 17.2 completo e ≥ 95% das fotos aceitas na primeira tentativa.

---

## Etapa 8 — Piloto na loja (1–2 semanas)

1. **Decidir** com o Claude Code: D6 (onde roda o worker: Mac da loja ou VPS), D8 (R2/S3 ou disco),
   D11 (página pública), D12 (amostra cega).
2. **Produção:** siga `deploy/README.md` (modelo do `producao.env`, serviços systemd do backend,
   worker e retenção, e launchd para o worker no Mac da loja). Peça ao Claude Code para adaptar ao
   servidor real da empresa; migração em produção só com seu pedido.
3. **Configurar a loja** no painel: modo **assistido**, amostra cega **100%** (isso inicia o modo sombra).
4. **10 sessões reais** com o técnico no painel; colete o retorno sobre a tela (meta: < 30 s por
   aparelho quando a sugestão está certa).
5. **Laudo:** confira o bloco "Estado estético" e a página de verificação em 2 ou 3 laudos.

**Pronto quando:** o técnico avalia pelo painel e a nota sai no laudo.

---

## Etapa 9 — Coleta e treino (semanas de uso)

1. **Toda semana:** abrir Concordância (só sessões cegas) e revisar com o Claude Code os casos
   discordantes. Ajustes de regra viram `criterio-v2`, nunca edição da v1.
2. **Cadastrar zonas** dos modelos de maior volume (ilha de câmeras, lentes, botões, porta, notch):
   `uv run python -I ferramentas/marcar_zonas.py <retificada.jpg> --face traseira --largura 71.5`
   numa foto de aparelho nota A, e conferir as dimensões com a Apple (`backend/app/estetica/dimensoes.py`).
3. **Detector:** com algumas centenas de defeitos marcados, peça ao Claude Code as etapas 12.3 e 12.4
   do guia (bases públicas com licença conferida, pré-treino, exportação, ajuste fino). Exige um Mac
   M-series ou GPU e `uv sync --extra treino`.
4. **PatchCore:** quando houver ≥ 100 faces nota A da mesma família de acabamento.

**Pronto quando:** sugestão boa o bastante para o gate (próxima etapa).

---

## Etapa 10 — Modo automático (decisão sua, por loja)

1. Depois de **14 dias** com amostra cega a 100%, abra Concordância → **Gate do modo automático**.
   Ele exige, só em aparelhos cegos do conjunto de teste: ≥ 200 aparelhos, ≥ 90% exato, zero erros
   de 2 notas, kappa ≥ o dos técnicos e recall ≥ 80% em cada nota.
2. Com o gate atendido, mude a loja para **automático** e a amostra cega para **5–10%**.
3. Se a qualidade cair, o sistema volta sozinho para assistido e mostra o aviso no painel.

---

## Decisões em aberto

| # | Decisão | Quando |
|---|---|---|
| D1–D4 | Luz rasante, altura da câmera, espelhos × suportes, contraluz | fim da etapa 3 |
| D5 | Lacunas L1–L10 do critério | etapa 4 |
| D6 | Onde roda o worker | etapa 8 |
| D7 | Detector: RF-DETR (padrão) ou Ultralytics pago | etapa 9 |
| D8 | Armazenamento R2/S3 | etapa 8 |
| D9–D12 | Confirmação no painel, pareamento, página pública, % cego | já com padrão; revisar na etapa 8 |

Em qualquer etapa, para retomar com o Claude Code:
> Leia o guia (seções 0 a 7), design.md, tasks.md e docs/passo-a-passo.md. Diga em que etapa estamos e continue.
