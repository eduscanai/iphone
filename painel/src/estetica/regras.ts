// Funções puras da tela de avaliação (testadas em regras.test.ts).
import { FACES, type Face, type Nota, NOTAS } from '../tipos'

export const pior = (...notas: Nota[]): Nota => notas.reduce((a, b) => (NOTAS.indexOf(b) > NOTAS.indexOf(a) ? b : a), 'A')

export function notaFinal(porFace: Record<Face, Nota>): Nota {
  return pior(...FACES.map((f) => porFace[f] ?? 'A'))
}

/** px/mm real da imagem retificada: o worker usa R ≥ px/mm nativo, que pode passar de 20. */
export function pxPorMm(larguraImagemPx: number, larguraFaceMm: number): number {
  return larguraImagemPx / larguraFaceMm
}

export function dimsFace(face: Face, d: { largura: number; altura: number; espessura: number }): [number, number] {
  if (face === 'frente' || face === 'traseira') return [d.largura, d.altura]
  if (face === 'lat_esq' || face === 'lat_dir') return [d.espessura, d.altura]
  return [d.largura, d.espessura]
}

export interface Ponto { x: number; y: number }

/** Caixa (em px da imagem) → mm no referencial da face, normalizada (w, h ≥ 0). */
export function caixaParaMm(a: Ponto, b: Ponto, r: number): [number, number, number, number] {
  const x = Math.min(a.x, b.x) / r, y = Math.min(a.y, b.y) / r
  const w = Math.abs(a.x - b.x) / r, h = Math.abs(a.y - b.y) / r
  return [arred(x), arred(y), arred(w), arred(h)]
}

export function linhaParaMm(a: Ponto, b: Ponto, r: number) {
  const pontos: [number, number][] = [[arred(a.x / r), arred(a.y / r)], [arred(b.x / r), arred(b.y / r)]]
  const comprimento = arred(Math.hypot(b.x - a.x, b.y - a.y) / r)
  return { pontos, comprimento, caixa: caixaParaMm(a, b, r) }
}

const arred = (v: number) => Math.round(v * 100) / 100

export const mm = (v: number | null | undefined, casas = 1) =>
  v == null ? '—' : `${v.toFixed(casas).replace('.', ',')} mm`

export const pct = (v: number | null | undefined) => (v == null ? '—' : `${(v * 100).toFixed(1).replace('.', ',')}%`)

/** Teclas da tela de avaliação (guia 11.2). */
export type Acao =
  | { tipo: 'face'; face: Face }
  | { tipo: 'nota'; nota: Nota }
  | { tipo: 'camada' }
  | { tipo: 'rejeitar' }
  | { tipo: 'desenhar' }
  | { tipo: 'salvar' }

export function acaoDaTecla(tecla: string): Acao | null {
  if (/^[1-6]$/.test(tecla)) return { tipo: 'face', face: FACES[Number(tecla) - 1] }
  const t = tecla.toUpperCase()
  if ((NOTAS as string[]).includes(t)) return { tipo: 'nota', nota: t as Nota }
  if (tecla === ' ') return { tipo: 'camada' }
  if (t === 'X') return { tipo: 'rejeitar' }
  if (t === 'N') return { tipo: 'desenhar' }
  if (tecla === 'Enter') return { tipo: 'salvar' }
  return null
}
