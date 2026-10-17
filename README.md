# Morecheck — nota estética automática

Nota estética **A/B/C/D** objetiva e auditável para iPhones usados. Uma cabine fotografa o aparelho
com luz ambiente e luz rasante; o worker de visão encontra e mede os defeitos em mm; o backend
aplica um critério versionado; o técnico confirma no painel; a nota vai para o laudo.

```
iPhone da cabine ──fotos──▶ backend (FastAPI + Postgres) ◀──tarefas── worker de visão (Python)
      │  luzes (ESP32)              │                                    retifica, mede, funde
      ▼                             ▼
aparelho avaliado (QR, tela preta)  painel (React): avaliação, concordância · laudo
```

> **Estado (outubro de 2026):** código pronto e testado no computador, com fotos sintéticas.
> Falta testar num iPhone de verdade, montar a cabine e integrar no sistema Morecheck existente
> (aqui, backend, painel e app usam substitutos marcados como STUB).

## Quero testar no meu iPhone

Siga **[docs/TESTE-IPHONE.md](docs/TESTE-IPHONE.md)**: prepara o Mac com um script, instala o app no
seu iPhone e roda os testes, sem precisar da cabine. No fim, mande os resultados numa issue
("Relato de teste no iPhone").

## Começar a desenvolver

Pré-requisitos: Mac com Homebrew. O script instala uv, Node, PostgreSQL 15 e xcodegen se faltarem.

```bash
scripts/configurar_dev.sh --instalar   # ambiente, segredos de desenvolvimento, bancos, dependências
scripts/subir_dev.sh                   # backend + painel em http://127.0.0.1:8000/painel/ + worker
scripts/simular_aparelho.sh            # um aparelho passando pela cabine (fotos sintéticas)
scripts/parar_dev.sh
```

Teste ponta a ponta isolado: `scripts/testar_local.sh`. Teste do app no simulador: `scripts/testar_simulador.sh`.

## Estrutura

| Pasta | O que é | Testes |
|---|---|---|
| [`backend/`](backend/) | FastAPI + Postgres: cabine, fila de visão, critério, avaliação, concordância, gate do modo automático, laudo | `uv run pytest` |
| [`visao/`](visao/) | Python: worker de visão, protótipos da fase 0, ferramentas de dados e treino | `uv run pytest` |
| [`painel/`](painel/) | React + TypeScript: fila, tela de avaliação, concordância, cabines | `npx vitest run` |
| [`app-ios/`](app-ios/) | SwiftUI: modo Cabine e tela QR + preto; lógica em `Pacotes/CabineNucleo` | `swift test` no pacote |
| [`hardware/`](hardware/) | Berço paramétrico (OpenSCAD/STL), montagem e firmware ESP32 das luzes | `pio run` |
| [`deploy/`](deploy/) | Modelos de produção: `producao.env`, systemd, launchd | — |
| [`scripts/`](scripts/) | Ambiente de desenvolvimento e testes | — |
| [`docs/`](docs/) | Guia, critério de nota, passo a passo, roteiro de testes, estudo da fase 1 | — |
| [`openspec/`](openspec/) | Especificação da mudança: decisões, divergências e tarefas | — |

## Documentos principais

- [Guia de implementação](docs/guia-claude-code-nota-estetica.md): arquitetura e **contratos** (seção 7 e 7.13).
- [Critério de nota (rascunho v1)](docs/nota-estetica-criterio.md).
- [Passo a passo do responsável](docs/passo-a-passo.md): o que falta para pôr em produção.
- [Decisões e riscos](openspec/changes/nota-estetica-automatica/design.md) · [Tarefas](openspec/changes/nota-estetica-automatica/tasks.md).

## Regras do projeto

- pt-BR em tudo: código, comentários, documentos e commits.
- Segredos só em `~/.morecheck/*.env`, nunca no repositório. A assinatura do app de cada pessoa
  fica em `app-ios/Config/Local.xcconfig`, também fora do Git.
- App iOS só com API pública. Sem dependências AGPL/GPL (o detector é RF-DETR, Apache-2.0).
