# Morecheck

Avaliação de iPhones usados: testes funcionais, laudo e nota estética.

- Idioma: pt-BR em tudo (código, comentários, mensagens, documentos, commits).
- Segredos só em `~/.morecheck/producao.env`. Nunca em código, logs ou commits.
- Não commitar, fazer push, migrar produção ou apagar dados sem pedido explícito.

## Nota estética automática
- Guia: docs/guia-claude-code-nota-estetica.md — leia as seções 0 a 7 antes de qualquer tarefa desta feature.
- PRD: docs/prd-nota-estetica.md · OpenSpec: openspec/changes/nota-estetica-automatica/
- Uma fase por vez. Nos pontos marcados PARADA, pare e peça ação ou decisão do responsável.

## Componentes e testes
- visao/ (uv, `uv run pytest`) · backend/ (uv, Postgres `morecheck_teste`, `uv run pytest`) · painel/ (`npx vitest run`) · app-ios/Pacotes/CabineNucleo (`swift test`) · hardware/
- Backend, painel e app são autônomos com STUBs (backend/app/base, app-ios/Sources/App): o código real do Morecheck não está neste repositório.
- Contratos: guia seção 7 + 7.13 (acréscimos da implementação). Mudou contrato → guia, design.md e os dois lados juntos.
