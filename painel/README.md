# painel — nota estética

React + TypeScript (Vite). Telas em `src/estetica/`: fila, avaliação (zoom 1:1, camadas,
desenho de defeito, atalhos 1–6 · A–D · espaço · X · N · Enter), concordância, gate e cabines.
Guia visual: amarelo `#F5C400`, tinta `#15191E`, Archivo e IBM Plex.

```bash
npm install
MORECHECK_API=http://127.0.0.1:8000 npm run dev
npx tsc -b && npx vitest run
```
