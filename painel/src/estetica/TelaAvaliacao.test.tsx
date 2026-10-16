import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { DetalheSessao, Face, Nota } from '../tipos'
import { TelaAvaliacao } from './TelaAvaliacao'

const FACES_A = { frente: 'A', traseira: 'A', lat_esq: 'A', lat_dir: 'A', topo: 'A', base: 'A' } as Record<Face, Nota>

function detalhe(cega = false): DetalheSessao {
  return {
    sessao_id: 's1', status: 'aguardando_tecnico', cega,
    aparelho: { identificador: 'iPhone14,5', nome: 'iPhone 13', cor: 'meia-noite', dimensoes_mm: { largura: 71.5, altura: 146.7, espessura: 7.65 }, zonas_mm: {}, raio_canto_mm: 9 },
    px_por_mm_retificacao: 20,
    fotos: [{ foto_id: 'f1', passo: 1, face: 'frente', luz: 'ambiente', tentativa: 1, aceita: true, qualidade: { ok: true }, faces_extraidas: ['frente'], original: null, retificada: { frente: '/r.jpg' }, anotada: {} }],
    sugestao: cega ? null : { id: 'g1', nota_final: 'B', notas_por_face: { ...FACES_A, frente: 'B' }, justificativas: {}, pendencias: [], versao_visao: '0.2.0', versao_criterio: 'criterio-v1', tempo_ms: 4000, margem_minima: 0.3 },
    defeitos_propostos: cega ? [] : [{ id: 'd1', face: 'frente', tipo: 'risco', zona: 'tela', visibilidade: 'so_rasante', origem: 'maquina', estado: 'proposto', caixa_mm: [10, 10, 5, 1], geometria_mm: null, comprimento_mm: 6, area_mm2: null, maior_dimensao_mm: 6, confianca: 0.9, fonte: 'opencv_riscos', foto_id: 'f1' }],
    avaliacoes: [], defeitos_avaliacao: [], registro_id: 'r1',
  }
}

let posts: { url: string; corpo: any }[] = [] // eslint-disable-line @typescript-eslint/no-explicit-any

function mockFetch(det: DetalheSessao) {
  posts = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, op?: RequestInit) => {
    if (op?.method === 'POST') {
      const corpo = JSON.parse(String(op.body))
      posts.push({ url, corpo })
      if (url === '/estetica/criterio/avaliar') {
        const temRisco = corpo.defeitos.some((d: { face: string }) => d.face === 'frente')
        const porFace = { ...FACES_A, frente: temRisco ? 'B' : 'A' }
        return new Response(JSON.stringify({ nota_final: porFace.frente, notas_por_face: porFace, justificativas: {}, pendencias: [], margem_minima: null }))
      }
      return new Response(JSON.stringify({ avaliacao_id: 'a1' }), { status: 201 })
    }
    return new Response(JSON.stringify(det))
  }))
}

describe('TelaAvaliacao', () => {
  beforeEach(() => vi.useRealTimers())
  afterEach(() => vi.unstubAllGlobals())

  it('confirma a sugestão com Enter e envia as decisões', async () => {
    mockFetch(detalhe())
    render(<TelaAvaliacao sessaoId="s1" onVoltar={() => {}} />)
    await screen.findByText('iPhone 13', { exact: false })
    await waitFor(() => expect(posts.some((p) => p.url === '/estetica/criterio/avaliar')).toBe(true))
    await waitFor(() => expect(screen.getByRole('button', { name: /Salvar/ })).toBeEnabled())
    await act(async () => { fireEvent.keyDown(window, { key: 'Enter' }) })
    await waitFor(() => expect(posts.some((p) => p.url === '/registros/r1/estetica')).toBe(true))
    const corpo = posts.find((p) => p.url === '/registros/r1/estetica')!.corpo
    expect(corpo.nota_final).toBe('B')
    expect(corpo.defeitos).toEqual([{ proposta_id: 'd1', estado: 'confirmado' }])
    expect(corpo.justificativa).toBeNull()
  })

  it('nota diferente da regra exige justificativa', async () => {
    mockFetch(detalhe())
    render(<TelaAvaliacao sessaoId="s1" onVoltar={() => {}} />)
    await screen.findByText('iPhone 13', { exact: false })
    await waitFor(() => expect(screen.getByRole('button', { name: /Salvar/ })).toBeEnabled())
    fireEvent.keyDown(window, { key: 'd' }) // nota D na face atual (frente)
    const salvar = screen.getByRole('button', { name: /Salvar/ })
    await waitFor(() => expect(salvar).toBeDisabled())
    fireEvent.change(screen.getByLabelText(/Justificativa/), { target: { value: 'Trinca sob a película' } })
    await waitFor(() => expect(salvar).toBeEnabled())
  })

  it('rejeitar a proposta recalcula a regra', async () => {
    mockFetch(detalhe())
    render(<TelaAvaliacao sessaoId="s1" onVoltar={() => {}} />)
    await screen.findByText('iPhone 13', { exact: false })
    fireEvent.click(await screen.findByRole('button', { name: 'Rejeitar' }))
    await waitFor(() => {
      const ultimas = posts.filter((p) => p.url === '/estetica/criterio/avaliar')
      expect(ultimas.at(-1)!.corpo.defeitos).toEqual([])
    })
  })

  it('sessão cega não mostra sugestão nem propostas', async () => {
    mockFetch(detalhe(true))
    render(<TelaAvaliacao sessaoId="s1" onVoltar={() => {}} />)
    expect(await screen.findByText(/Sessão cega/)).toBeInTheDocument()
    expect(screen.queryByText(/Sugestão da máquina/)).toBeNull()
  })
})
