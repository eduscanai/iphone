## Context

O guia de implementação (`docs/guia-claude-code-nota-estetica.md`) é a fonte técnica desta mudança: arquitetura (seção 5), mapa de arquivos (seção 6) e **contratos** (seção 7) valem como especificação. O PRD v1.0 (`docs/prd-nota-estetica.md`) define o quê e o porquê.

Componentes: app iOS em modo Cabine, aparelho avaliado (tela QR + preto), ESP32 de luzes, backend FastAPI + Postgres, worker de visão em Python, painel React e laudo.

Restrições: app iOS só com API pública; pt-BR em tudo; segredos só em `~/.morecheck/producao.env`; nenhuma dependência AGPL/GPL sem aprovação; Python com `uv`.

## Goals / Non-Goals

**Goals:**
- Nota A/B/C/D objetiva, repetível e auditável, com fotos e defeitos em mm no laudo.
- Cabine ≤ 60 s por aparelho; sugestão ≤ 10 s após a última foto.
- Dados de treino a partir das correções dos técnicos; concordância medida sem viés (amostra cega).
- Modo automático por loja, liberado só por gate estatístico.

**Non-Goals:**
- Robô/esteira (fase 2B), Android, iPad, Apple Watch.
- Avaliação com tela ligada (pixel morto já é teste funcional).
- Polimento e reparo.

## Decisions

Ajustes propostos em relação ao PRD (guia, seção 3) e decisões do responsável (guia, seção 4). Preencher a coluna "Situação" na primeira sessão; ajuste recusado = seguir o PRD.

### Ajustes R1–R22

| # | Tema | Proposta | Situação | Data |
|---|---|---|---|---|
| R1 | Luz rasante | 2 barras a 90° (`rasante_a`, `rasante_b`) | aceito, a validar na fase 0 | 2026-10-15 |
| R2 | Foco | `lensPosition` calibrado por pose | aceito, a validar na fase 0 | 2026-10-15 |
| R3 | Laterais, topo, base | espelhos a 45°, aparelho sempre deitado | aceito, a validar na fase 0 | 2026-10-15 |
| R4 | Resolução de análise | detectar na nativa; retificar ≥ 20 px/mm | aceito, a validar na fase 0 | 2026-10-15 |
| R5 | Altura da câmera | escolher pelo px/mm alvo (~25 cm com 48 MP) | aceito, a validar na fase 0 | 2026-10-15 |
| R6 | Película, capa, sujeira | retirar e limpar com microfibra (processo) | aceito | 2026-10-15 |
| R7 | PatchCore | por família de acabamento, traseira e moldura, em blocos | aceito | 2026-10-15 |
| R8 | Amassado | diâmetro aparente na rasante | aceito | 2026-10-15 |
| R9 | "Visível" | olho nu a ~30 cm na luz da bancada | aceito | 2026-10-15 |
| R10 | Meta do automático | + kappa ≥ linha de base; recall ≥ 80% por nota; só amostra cega | aceito | 2026-10-15 |
| R11 | Amostra cega | parte das sessões esconde a sugestão | aceito | 2026-10-15 |
| R12 | Armazenamento | object storage S3-compatível | aceito | 2026-10-15 |
| R13 | Quem calcula a nota | backend (motor versionado); visão só devolve defeitos | aceito | 2026-10-15 |
| R14 | Fila | tabela Postgres + worker que puxa por HTTPS | aceito | 2026-10-15 |
| R15 | Detector | RF-DETR (Apache-2.0) | aceito | 2026-10-15 |
| R16 | Contorno | OpenCV (+ contraluz); RF-DETR-Seg como plano B | aceito, a validar na fase 0 | 2026-10-15 |
| R17 | Exposição | múltiplo de 1/120 s (rede 60 Hz) | aceito | 2026-10-15 |
| R18 | Tela preta | preto + brilho 0 | aceito | 2026-10-15 |
| R19 | Envio | foto a foto, com `Idempotency-Key` | aceito | 2026-10-15 |
| R20 | Processamento | uma tarefa por foto + fusão no fim | aceito | 2026-10-15 |
| R21 | Orientação | rotação fixa no app; EXIF ignorado | aceito | 2026-10-15 |
| R22 | `anomalia` | região do PatchCore vira defeito revisado pelo técnico | aceito | 2026-10-15 |

### Decisões D1–D12

| # | Decisão | Padrão enquanto não decidida | Decisão | Data |
|---|---|---|---|---|
| D1 | Direções da luz rasante | duas barras, fotos separadas | padrão, provisório até o relatório da fase 0 | 2026-10-15 |
| D2 | Altura da câmera / px/mm | ≥ 20 px/mm respeitando foco mínimo | padrão, provisório até o relatório da fase 0 | 2026-10-15 |
| D3 | Laterais, topo e base | espelhos, se nítidos na fase 0 | padrão, provisório até o relatório da fase 0 | 2026-10-15 |
| D4 | Foto de contraluz | sim, se contorno falhar em > 2% | padrão, provisório até o relatório da fase 0 | 2026-10-15 |
| D5 | Lacunas do critério (guia 16.4) | "a definir", nunca automáticas | padrão (provisório) | 2026-10-15 |
| D6 | Onde roda o worker | Mac da loja (treino); VPS (OpenCV) | padrão (provisório) | 2026-10-15 |
| D7 | Detector | RF-DETR | padrão (provisório) | 2026-10-15 |
| D8 | Armazenamento | R2; disco só em desenvolvimento | padrão (provisório) | 2026-10-15 |
| D9 | Onde o técnico confirma | só no painel | padrão (provisório) | 2026-10-15 |
| D10 | Pareamento da cabine | sim | padrão (provisório) | 2026-10-15 |
| D11 | Página pública de verificação | miniaturas + defeitos, sem originais | padrão (provisório) | 2026-10-15 |
| D12 | Percentual cego | 100% nas 2 primeiras semanas; depois 10% | padrão (provisório) | 2026-10-15 |

### Divergências do guia

<!-- Registrar aqui: data, o que divergiu, motivo, alternativa, impacto. -->

| Data | O que | Motivo | Impacto |
|---|---|---|---|
| 2026-10-16 | `visao/` em Python 3.12 (guia: mesma versão do backend) | backend ainda não está no repositório | alinhar quando o backend entrar |
| 2026-10-16 | Módulo extra `src/visao/fase0.py` e scripts `conferir_fotos.py`, `cruzar_anotacao.py`, `rodar_tudo.sh` (fora do mapa da seção 6) | apoio comum aos protótipos; passo 9 da seção 8.3 não tinha script nomeado | só fase 0 |
| 2026-10-16 | Marcadores ArUco desenhados como vetores no PDF | imagens raster no PDF do matplotlib erravam o tamanho em até 0,25 mm | nenhum; escala conferida a 1200 dpi (30,00 ± 0,02 mm) |
| 2026-10-16 | `io_imagem.ler()` devolve só cinza por padrão (cor com `com_cor=True`) | foto de 48 MP em cor float32 ocupa ~580 MB; Mac de 8 GB entrava em swap | detecção usa luminância (guia 15.1); sem impacto |
| 2026-10-16 | Contorno: varredura de limiares + escolha por proporção/área, antes do ajuste de retas | um objeto claro na cena (folha de marcadores) desloca o Otsu | nenhum no contrato |
| 2026-10-16 | Backend, painel e app iOS criados como projetos autônomos, com STUBs de `loja`, `usuario`, `sessao`, `registro`, `auditoria` e autenticação (`backend/app/base/`, `app-ios/Sources/App/`) | o código atual do Morecheck não está neste repositório | na integração: apagar os stubs, apontar as FKs para as tabelas reais e mover os módulos para dentro dos projetos existentes (seguindo o estilo deles) |
| 2026-10-16 | Contratos acrescidos (guia 7.13): `PUT /cabine/perfil`, `GET /cabine/{token}/eventos`, `GET /cabines`, upload por face, formato da tarefa `fusao`, colunas novas | o contrato 7.x não cobria perfil para o worker, faces múltiplas por foto (espelhos), holdout por aparelho nem modo sombra | guia v1.1 |
| 2026-10-16 | Nitidez medida na faixa de ±1 mm do contorno, normalizada pela energia do gradiente (guia 14.6 dizia "dentro do aparelho") | tela apagada é lisa: a variância do Laplaciano dentro do aparelho reprovaria fotos nítidas | limiar 4,5 provisório, a recalibrar na fase 2 |
| 2026-10-16 | Camada (a) não procura riscos a menos de `faixa_busca_mm` = 1,5 mm da borda (a zona `moldura` continua 0,5 mm) | o friso da moldura e a borda curva do vidro brilham na rasante e viram falsos riscos | provisório: a fase 0 mede (`perto_borda`) e decide; riscos nessa faixa ficam para o detector (c) e o técnico |
| 2026-10-16 | Piso no MAD da camada (a) (meio nível de 8 bits) | vidro liso + compressão dá MAD ≈ 0: o limiar zerava e o ruído ligava tudo, sumindo riscos reais | nenhum no contrato; teste de regressão |
| 2026-10-16 | Camada (a) roda na face retificada a R = máx(20, px/mm nativo), não na foto original | R ≥ resolução nativa não perde detalhe (R4) e as medidas já saem em mm no referencial 7.2 | nenhum |
| 2026-10-16 | Orientação: só resta a ambiguidade de 180°; resolvida pelo `perfil.orientacao` (batente) e conferida na traseira pela textura da ilha de câmeras | a retificação sempre sai em retrato; o batente fixa o topo | orientação dentro dos espelhos ainda não conferida (`orientacao_ok = null`) até a cabine montada |
| 2026-10-16 | App iOS: lógica num pacote Swift (`CabineNucleo`) testado no Mac; app só com checagem de tipos contra o SDK do iPhone | sem runtime de simulador instalado (download ~8 GB) e sem o projeto real | instalar no iPhone na PARADA da fase 2 (Xcode com a plataforma iOS) |
| 2026-10-16 | Detector (RF-DETR) e PatchCore escritos mas não executados; dependências em `--extra treino` | sem dados próprios ainda e sem PyTorch instalado | VERIFICAR as APIs (`rfdetr`, `anomalib`) na primeira execução |
| 2026-10-16 | Berço com batentes só nas quinas e espelhos de 12 mm em trilhos | batente contínuo esconderia a base das laterais no espelho; cunha alta faz sombra na rasante (ver Riscos) | foto `espelho_frente_ra` na fase 0 |

## Risks / Trade-offs

Lista completa no guia, seção 19. Principais:

- [Risco paralelo à luz rasante some] → duas direções de luz (R1), validado na fase 0.
- [Poeira e digital viram risco] → limpeza obrigatória; filtro de alongamento; comparar as duas luzes.
- [Aparelho preto em fundo preto] → contraluz (D4); moldura realçada na rasante.
- [Viés de automação infla a concordância] → amostra cega (R11).
- [Vazamento entre treino e teste] → separar por aparelho; holdout congelado.
- [Licença do detector] → RF-DETR em vez de Ultralytics (R15).
- [Worker parado] → painel funciona sem sugestão; alerta se a fila passar de 5 min.
- [**Conflito R1 × R3**, achado em 2026-10-16 ao modelar o berço] Com espelhos a 45° nos 4 lados, cada barra rasante fica atrás de um espelho. Raio rasante vindo de ~20 cm a 1–2 cm de altura passa a ~8 mm sobre a cunha; cunha mais alta faz sombra na tela. Duas viradas com 2 espelhos não cobrem as 4 laterais (cada virada troca um só par de lados). → Cunha limitada a ~9,5 mm (espelho de 12 mm, `berco.scad`); foto `espelho_frente_ra` na fase 0 mede a sombra. Se houver sombra: espelhos rebatíveis (só na foto `ambiente`), barras mais altas (menos rasante) ou D3 = suportes em pé.

## Migration Plan

1. Fases 0 a 5 em ordem (guia, seções 8 a 13), com PARADA ao fim de cada uma.
2. Migração Alembic com `downgrade`; nada em produção sem pedido explícito.
3. Lojas começam em `desligado` → `assistido` → (gate) `automatico`. Rollback: voltar a loja para `assistido` pelo painel ou automaticamente pelo monitoramento.

## Open Questions

- Decisões D1–D12 acima.
- Lacunas L1–L10 do critério (guia, seção 16.4).
- PRD v1.0 ainda não está no repositório (`docs/prd-nota-estetica.md`): o critério v1 foi redigido a partir do resumo do PRD §10 no guia.
- Código existente do Morecheck (backend, app-ios, painel, laudo): integração dos módulos novos (ver Divergências).
