## Why

Hoje a nota estética (A/B/C/D) de cada iPhone usado depende só do olho do técnico: varia entre pessoas, não deixa evidência e não escala para ~4.000 aparelhos/mês (~200/dia). Como a nota define preço e canal de venda (venda direta, reparo/polimento, peças), precisamos de uma nota **objetiva, repetível e auditável**, com fotos e defeitos medidos em mm no laudo.

## What Changes

- Nova **cabine A**: um iPhone da empresa fixo, em modo Cabine, fotografa cada face com luz ambiente e luz rasante (2 direções), controlando as luzes por um ESP32 e disparando sozinho quando a imagem fica estável.
- O **aparelho avaliado** mostra o QR da sessão e apaga a tela sob comando (preto + brilho 0).
- Novo **worker de visão** (`visao/`, Python): qualidade, retificação usando o próprio aparelho como régua, detecção de riscos (OpenCV), anomalias (PatchCore) e defeitos (RF-DETR), medição em mm e fusão por face.
- Novo **motor de critério** versionado no backend (`criterio-v1.yaml`): defeitos → notas por face → nota final, com justificativas e margens.
- Novo **painel de avaliação**: o técnico confirma ou corrige a sugestão; correções viram dado de treino; amostra cega mede a concordância sem viés de automação.
- **Laudo** ganha o bloco "Estado estético" (nota, origem, miniaturas, defeitos, versão do critério).
- **Modo automático** por loja, liberado só por um gate estatístico (≥ 200 aparelhos cegos, ≥ 90% exato, 0 erros de 2 notas, kappa ≥ linha de base humana, recall ≥ 80% por nota).

## Capabilities

### New Capabilities
- `captura-cabine`: app modo Cabine, pareamento, calibração, roteiro de faces, controle de luz (ESP32), tela QR + preto do aparelho avaliado, envio idempotente das fotos.
- `pipeline-visao`: fila de tarefas, worker que puxa por HTTPS, qualidade, geometria, retificação, camadas (a) riscos, (b) PatchCore, (c) RF-DETR, fusão e medição.
- `criterio-nota`: critério escrito e versionado, motor puro que converte defeitos em notas.
- `avaliacao-estetica`: sessões, sugestão, fila e tela de avaliação no painel, amostra cega, relatório de concordância.
- `laudo-estetico`: bloco "Estado estético" no laudo PDF e na página de verificação.
- `modo-automatico`: gate, modo sombra, automação seletiva e monitoramento contínuo.

### Modified Capabilities
<!-- Nenhuma spec existente em openspec/specs/. -->

## Impact

- **Backend:** módulo novo `backend/app/estetica/`, migração Alembic (8 tabelas), rotas de cabine, página, painel e visão; integração em `backend/app/laudo/`.
- **App iOS:** `app-ios/Sources/Cabine/` e `app-ios/Sources/Estetica/TelaQRPreto.swift`; permissões de câmera e rede local.
- **Painel:** `painel/src/estetica/`.
- **Novo pacote:** `visao/` (uv). **Hardware:** `hardware/cabine-a/`, `hardware/cabine-luz/`.
- **Infra:** object storage S3-compatível (R2), de ~0,15 a ~0,5 TB/mês; worker num Mac da loja ou VPS.
- **Licenças:** RF-DETR (Apache-2.0) no lugar de Ultralytics (AGPL); só bases públicas de uso comercial permitido.
- Contratos detalhados: `docs/guia-claude-code-nota-estetica.md`, seção 7.
