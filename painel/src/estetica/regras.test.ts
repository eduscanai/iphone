import { describe, expect, it } from 'vitest'
import { acaoDaTecla, caixaParaMm, dimsFace, linhaParaMm, mm, notaFinal, pior, pxPorMm } from './regras'

describe('regras do painel', () => {
  it('pior nota e nota final = pior face', () => {
    expect(pior('A', 'C', 'B')).toBe('C')
    expect(notaFinal({ frente: 'B', traseira: 'A', lat_esq: 'A', lat_dir: 'D', topo: 'A', base: 'A' })).toBe('D')
  })
  it('converte desenho em px da retificada para mm', () => {
    const r = pxPorMm(1430, 71.5) // retificada a 20 px/mm
    expect(r).toBe(20)
    expect(caixaParaMm({ x: 300, y: 100 }, { x: 200, y: 140 }, r)).toEqual([10, 5, 5, 2])
    const l = linhaParaMm({ x: 0, y: 0 }, { x: 60, y: 80 }, r)
    expect(l.comprimento).toBe(5)
    expect(l.pontos).toEqual([[0, 0], [3, 4]])
  })
  it('dimensões da face no referencial 7.2', () => {
    const d = { largura: 71.5, altura: 146.7, espessura: 7.65 }
    expect(dimsFace('traseira', d)).toEqual([71.5, 146.7])
    expect(dimsFace('lat_esq', d)).toEqual([7.65, 146.7])
    expect(dimsFace('topo', d)).toEqual([71.5, 7.65])
  })
  it('atalhos de teclado', () => {
    expect(acaoDaTecla('3')).toEqual({ tipo: 'face', face: 'lat_esq' })
    expect(acaoDaTecla('c')).toEqual({ tipo: 'nota', nota: 'C' })
    expect(acaoDaTecla(' ')).toEqual({ tipo: 'camada' })
    expect(acaoDaTecla('x')).toEqual({ tipo: 'rejeitar' })
    expect(acaoDaTecla('Enter')).toEqual({ tipo: 'salvar' })
    expect(acaoDaTecla('7')).toBeNull()
  })
  it('formata mm em pt-BR', () => {
    expect(mm(9.8)).toBe('9,8 mm')
    expect(mm(null)).toBe('—')
  })
})
