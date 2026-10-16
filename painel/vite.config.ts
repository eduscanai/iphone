/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Em desenvolvimento, a API (backend FastAPI) responde em MORECHECK_API (padrão :8000).
const api = process.env.MORECHECK_API ?? 'http://127.0.0.1:8000'
const rotas = ['/estetica', '/registros', '/arquivos', '/laudo', '/cabines', '/verificar']

export default defineConfig({
  plugins: [react()],
  server: { proxy: Object.fromEntries(rotas.map((r) => [r, api])) },
  test: { environment: 'jsdom', setupFiles: ['./src/testes/preparar.ts'], globals: true },
})
