# Morecheck — nota estética automática

Nota estética A/B/C/D objetiva e auditável para iPhones usados: uma cabine fotografa o aparelho
com luz ambiente e rasante, o worker de visão mede os defeitos em mm, o backend aplica o critério
versionado e o técnico confirma no painel.

- Guia de implementação: [docs/guia-claude-code-nota-estetica.md](docs/guia-claude-code-nota-estetica.md) (contratos na seção 7)
- Critério (rascunho v1): [docs/nota-estetica-criterio.md](docs/nota-estetica-criterio.md)
- Mudança OpenSpec: [openspec/changes/nota-estetica-automatica/](openspec/changes/nota-estetica-automatica/) — decisões e divergências em `design.md`, andamento em `tasks.md`

> **Estado:** os módulos novos foram construídos como projetos autônomos, com STUBs no lugar do
> backend, do app e do painel atuais do Morecheck (que não estão neste repositório). A fase 0
> (fotos reais) e as PARADAS de cada fase dependem do responsável.

**O que fazer agora:** [docs/passo-a-passo.md](docs/passo-a-passo.md) · teste rápido: `scripts/testar_local.sh`

## Componentes

| Pasta | O que é | Testes |
|---|---|---|
| `visao/` | Python (uv): protótipos da fase 0, worker de visão (camadas a, b e c), fusão, ferramentas | `uv run pytest` (44) |
| `backend/` | FastAPI + Postgres: módulo `app/estetica` (cabine, fila, eventos, critério, avaliação, concordância, gate), bloco do laudo | `uv run pytest` (71, Postgres real) |
| `painel/` | React + TypeScript (Vite): fila, tela de avaliação, concordância, cabines | `npx vitest run` (10) |
| `app-ios/` | Modo Cabine e tela QR + preto (SwiftUI, AVFoundation); lógica em `Pacotes/CabineNucleo` | `swift test` no pacote (21) |
| `hardware/cabine-a/` | Berço paramétrico (OpenSCAD + STL), lista de compras, montagem, ligação | — |
| `hardware/cabine-luz/` | Firmware ESP32 (PlatformIO) das luzes | `pio run` compila |

## Rodar em desenvolvimento

Pré-requisitos: Python 3.12 + [uv](https://docs.astral.sh/uv/), PostgreSQL 15, Node 20+, Xcode 16 (app), PlatformIO (firmware).

```bash
# 1. Banco e backend
createdb morecheck_dev
cd backend
DATABASE_URL=postgresql+psycopg://localhost/morecheck_dev uv run alembic upgrade head
export DATABASE_URL=postgresql+psycopg://localhost/morecheck_dev VISAO_WORKER_TOKENS=tok-dev URL_PUBLICA=http://127.0.0.1:8000
uv run python -m app.dev semear > /tmp/dev.json          # loja, técnico, admin, cabine (tokens)
uv run python -m app.dev sessao --dados /tmp/dev.json > /tmp/sessao.json
uv run uvicorn app.main:app --port 8000

# 2. Worker de visão (outro terminal)
cd visao
MORECHECK_API_URL=http://127.0.0.1:8000 VISAO_WORKER_TOKEN=tok-dev uv run python -m visao.worker   # --nulo para a fase 3

# 3. Simular a cabine com fotos no padrão da fase 0 (outro terminal)
uv run python -I ferramentas/simular_cabine.py --api http://127.0.0.1:8000 \
  --dados /tmp/dev.json --sessao /tmp/sessao.json --fotos prototipos/fotos --aparelho 1

# 4. Painel
cd painel && npm install && MORECHECK_API=http://127.0.0.1:8000 npm run dev   # entrar com o token do técnico
```

Segredos de produção só em `~/.morecheck/producao.env` (o backend também lê `~/.morecheck/desenvolvimento.env`).

## Testes

```bash
cd backend && createdb morecheck_teste && uv run pytest      # migração sobe do zero a cada rodada
cd visao && uv run pytest
cd painel && npx tsc -b && npx vitest run
cd app-ios/Pacotes/CabineNucleo && swift test
```

## Fase 0

Protocolo de fotos: [visao/prototipos/PROTOCOLO.md](visao/prototipos/PROTOCOLO.md). Depois das fotos:
`cd visao && uv run python -I prototipos/conferir_fotos.py && prototipos/rodar_tudo.sh <altura_mm>`.
