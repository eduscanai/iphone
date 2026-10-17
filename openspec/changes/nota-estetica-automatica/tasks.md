## 0. Preparação

- [ ] 0.1 Colocar o PRD em docs/prd-nota-estetica.md
- [ ] 0.2 Trazer o código existente do Morecheck (backend, app-ios, painel, laudo) e integrar os módulos novos (trocar os STUBs; ver design.md → Divergências)
- [x] 0.3 Apresentar ajustes R1–R22 e decisões D1–D12 ao responsável e registrar em design.md

## 1. Fase 0 — Teste na mão (guia, seção 8)

- [x] 1.1 Criar o pacote visao/ com uv e dependências da fase 0
- [x] 1.2 gerar_marcadores.py → marcadores.pdf (vetorial; conferido a 1200 dpi: 30,00 ± 0,02 mm)
- [x] 1.3 src/visao/io_imagem.py: HEIC, DNG e JPEG em float32, ignorando EXIF
- [x] 1.4 medir_escala.py (ArUco × contorno, com e sem contraluz, altura estimada)
- [x] 1.5 riscos.py (camada a sobre ra, rb e união)
- [x] 1.6 comparar_iluminacao.py e comparar_resolucao.py
- [x] 1.7 profundidade_foco.py (deitado, lateral, ponta, espelho)
- [ ] 1.8 PARADA: humano tira as fotos seguindo visao/prototipos/PROTOCOLO.md e preenche anotacao.csv
- [ ] 1.9 Rodar cruzar_anotacao.py com as fotos reais (script pronto)
- [ ] 1.10 Rodar prototipos/rodar_tudo.sh → docs/nota-estetica-fase0-relatorio.md (validado com fotos sintéticas)
- [ ] 1.11 PARADA: responsável decide D1–D4 (atenção ao conflito R1 × R3 em design.md → Riscos); registrar em design.md

## 2. Fase 1 — Critério de nota (guia, seção 9)

- [x] 2.1 Rascunho de docs/nota-estetica-criterio.md (zonas, tipos, medidas, regras, 14 exemplos, lacunas L1–L10)
- [x] 2.2 criterios/criterio-v1.yaml + esquema Pydantic estrito
- [x] 2.3 Motor criterio.py (função pura) com testes de exemplos e de propriedades (hypothesis)
- [x] 2.4 Modelo docs/estudo-concordancia-v1.csv
- [x] 2.5 visao/ferramentas/concordancia.py (exata, ±1, ≥ 2 notas, kappa quadrático, matriz 4×4, divergências)
- [ ] 2.6 Conferir o critério contra o PRD §10 (o rascunho veio do resumo no guia)
- [ ] 2.7 PARADA: dois técnicos avaliam 20 aparelhos às cegas; reunião de divergências; fechar L1–L10
- [ ] 2.8 PARADA: aprovação do criterio-v1 (≥ 85% exato e kappa ≥ 0,80); gravar o kappa em ESTETICA_KAPPA_TECNICOS

## 3. Fase 2 — Cabine A (guia, seção 10)

- [x] 3.1 hardware/cabine-a/README.md (compras, montagem, ligação elétrica, conferências, risco da sombra dos espelhos)
- [x] 3.2 berco.scad paramétrico e STLs (berço, suporte de espelho, suporte de LED)
- [x] 3.3 Firmware hardware/cabine-luz/ (PWM 20 kHz, API 7.10, desligamento em 120 s) — compila (PlatformIO)
- [ ] 3.4 PARADA: humano compra, imprime, monta a cabine e grava o ESP32
- [x] 3.5 App: pareamento (QR/código → Keychain) e configuração das luzes
- [x] 3.6 App: assistente de calibração e PerfilCamera (14.3)
- [x] 3.7 App: máquina de estados do roteiro (pura, testada), captura, estabilidade e qualidade local
- [x] 3.8 App: fila de envio persistente com Idempotency-Key; fim de sessão, sugestão e refazer
- [x] 3.9 Tela QR + preto no aparelho avaliado (nativo)
- [x] 3.10 Testes da lógica pura (swift test, 21 testes) e checagem de tipos do app contra o SDK iOS
- [x] 3.10a App compilado e testado no simulador: tela QR + preto e pareamento (scripts/testar_simulador.sh)
- [ ] 3.10b Teste num iPhone real por colaborador (docs/TESTE-IPHONE.md)
- [ ] 3.11 Integrar Sources/Cabine e Sources/Estetica no app real (project.yml existente)
- [ ] 3.12 PARADA: instalar no iPhone da cabine, calibrar, rodar o checklist 17.2; medir ≤ 60 s com técnico real; calibrar limiares (nitidez, movimento, mão)

## 4. Fase 3 — Backend, painel e laudo (guia, seção 11)

- [x] 4.1 Migração Alembic das tabelas da seção 7.8 (+ 7.13), com downgrade testado
- [x] 4.2 dimensoes.py (Apêndice A) — 26 modelos, XR ao 16 Pro Max; VERIFICAR valores e MEDIR raio e zonas
- [x] 4.3 armazenamento.py (disco com URL assinada HMAC, e s3/R2)
- [x] 4.4 Rotas de cabine, página, painel e visão com escopo por loja e auditoria
- [x] 4.5 Fila (SKIP LOCKED, lease, liberação condicionada, prioridade da fusão) e eventos (long-poll)
- [x] 4.6 Motor de critério ligado à fusão; rota /estetica/criterio/avaliar
- [x] 4.7 Amostra cega (sorteio por loja; sugestão escondida até a avaliação)
- [x] 4.8 Worker nulo (visao worker --nulo)
- [x] 4.9 Retenção diária (python -m app.estetica.retencao)
- [x] 4.10 Painel: fila e tela de avaliação com atalhos, desenho de defeito e camadas
- [x] 4.11 Painel: relatório de concordância, gate, configuração da loja e pareamento de cabines
- [x] 4.12 Laudo: bloco "Estado estético" (JSON e HTML) e página pública de verificação (D11)
- [x] 4.13 simular_cabine.py ponta a ponta (fotos sintéticas: nota certa, 6,7 s após a última foto)
- [ ] 4.14 Integrar o bloco no gerador de PDF do laudo real e a página de verificação real
- [ ] 4.15 PARADA: técnico usa o painel em 10 sessões reais e dá retorno sobre a tela

## 5. Fase 4 — Nota sugerida (guia, seção 12)

- [x] 5.1 Worker real (cliente_api.py, worker.py, renovação de lease, log estruturado)
- [x] 5.2 Qualidade, geometria, orientação e retificação
- [x] 5.3 Camada (a), visibilidade, fusão, medição e zonas
- [x] 5.4 Relatório de concordância com dados reais (rota e painel prontos; falta dado)
- [ ] 5.5 Rodar o worker como serviço (launchd no Mac ou systemd na VPS) — decidir D6
- [x] 5.6 Ferramentas: baixar_bases.py (com trava de licença), exportar_dataset.py (divisão por aparelho), treinar_detector.py, treinar_patchcore.py, marcar_zonas.py
- [x] 5.7 Camadas (b) e (c) integradas ao worker (carregadas se houver modelo; senão só a camada a)
- [x] 5.8a Validar a cadeia de treino com dados sintéticos (rfdetr 1.11, anomalib 2.7): ferramentas/teste_treino.py; PatchCore com notas brutas
- [ ] 5.8 Baixar bases permitidas, pré-treinar o RF-DETR (em máquina com mais memória/GPU) e medir nas fotos da fase 0
- [ ] 5.9 Ajuste fino com as marcações do painel; PatchCore quando houver ≥ 100 faces nota A por família
- [ ] 5.10 Verificar ≤ 10 s (p95) com fotos de 48 MP e recall ≥ 90% para riscos ≥ 3 mm
- [ ] 5.11 PARADA: revisão semanal do relatório de concordância

## 6. Fase 5 — Modo automático (guia, seção 13)

- [x] 6.1 Gate em PUT /estetica/config (409 com os motivos; só holdout cego; regra de três no relatório)
- [x] 6.2 Modo sombra (sombra_iniciada_em; 14 dias com 100% cego)
- [x] 6.3 Automação seletiva (margem, a_definir, anomalia, trinca de confiança intermediária, faces sem foto)
- [x] 6.4 Monitoramento contínuo (janela de 200 cegas) e retorno automático para assistido, com aviso no painel
- [ ] 6.5 PARADA: responsável decide ligar o automático, por loja
