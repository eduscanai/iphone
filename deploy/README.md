# Implantação (etapa 8 do passo a passo)

Modelos genéricos: ajuste ao servidor real da empresa. Migração em produção só com pedido explícito.

1. **Segredos:** `cp producao.env.exemplo ~/.morecheck/producao.env`, preencher, `chmod 600`.
2. **Storage (D8):** criar o bucket R2 `morecheck-estetica` (privado) e uma chave de API só para ele.
3. **Banco:** `cd backend && uv run alembic upgrade head` (no Morecheck real, a migração da estética depende da última revisão real, sem a `0001_base_stub`).
4. **Painel:** `cd painel && npm ci && npm run build` → o backend serve `painel/dist` em `/painel` (ou `PAINEL_DIR`).
5. **Backend (VPS):** `systemd/morecheck-backend.service` atrás de um proxy com TLS.
6. **Retenção:** `systemd/morecheck-retencao.timer` (diário).
7. **Worker:** VPS (`systemd/morecheck-worker.service`, só camada a) ou Mac da loja (`launchd/com.morecheck.worker.plist`, com detector e PatchCore via MPS).
8. **Conferir:** `curl https://<api>/saude` e o painel em `https://<api>/painel/`; rodar `simular_cabine.py` contra a produção com uma sessão de teste.
