// Face retificada com zoom (roda), arrasto, 1:1 e camadas (guia 11.2). Desenha defeitos em SVG
// no próprio espaço da imagem: 1 px da imagem = 1/R mm.
import { useCallback, useEffect, useRef, useState } from 'react'
import type { Defeito, DefeitoNovo } from '../tipos'
import { CORES } from './cores'
import type { Ponto } from './regras'

export interface Camada { nome: string; url: string }
export type Ferramenta = 'caixa' | 'linha' | null

interface Props {
  camadas: Camada[]
  camadaAtiva: number
  mostrarDefeitos: boolean
  propostas: (Defeito & { rejeitado: boolean })[]
  novos: DefeitoNovo[]
  selecionado: string | null
  ferramenta: Ferramenta
  larguraMm: number
  onSelecionar: (id: string) => void
  onDesenhado: (a: Ponto, b: Ponto, r: number) => void
  onR?: (r: number) => void
}

export function VisualizadorFace(p: Props) {
  const caixa = useRef<HTMLDivElement>(null)
  const [tam, setTam] = useState<{ w: number; h: number } | null>(null)
  const [escala, setEscala] = useState(1)
  const [desl, setDesl] = useState({ x: 0, y: 0 })
  const arrasto = useRef<{ x: number; y: number; dx: number; dy: number } | null>(null)
  const [desenho, setDesenho] = useState<{ a: Ponto; b: Ponto } | null>(null)
  const url = p.camadas[p.camadaAtiva]?.url ?? p.camadas[0]?.url
  const r = tam ? tam.w / p.larguraMm : 1

  const ajustar = useCallback(() => {
    const el = caixa.current
    if (!el || !tam) return
    const s = Math.min(el.clientWidth / tam.w, el.clientHeight / tam.h)
    setEscala(s)
    setDesl({ x: (el.clientWidth - tam.w * s) / 2, y: (el.clientHeight - tam.h * s) / 2 })
  }, [tam])

  useEffect(() => { ajustar() }, [ajustar])
  useEffect(() => { if (tam) p.onR?.(tam.w / p.larguraMm) }, [tam, p.larguraMm]) // eslint-disable-line react-hooks/exhaustive-deps

  const paraImagem = (ev: { clientX: number; clientY: number }): Ponto => {
    const ret = caixa.current!.getBoundingClientRect()
    return { x: (ev.clientX - ret.left - desl.x) / escala, y: (ev.clientY - ret.top - desl.y) / escala }
  }

  const roda = (ev: React.WheelEvent) => {
    ev.preventDefault()
    const ret = caixa.current!.getBoundingClientRect()
    const cx = ev.clientX - ret.left, cy = ev.clientY - ret.top
    const nova = Math.min(8, Math.max(0.05, escala * (ev.deltaY < 0 ? 1.2 : 1 / 1.2)))
    setDesl({ x: cx - ((cx - desl.x) * nova) / escala, y: cy - ((cy - desl.y) * nova) / escala })
    setEscala(nova)
  }

  const umPraUm = () => {
    const el = caixa.current!
    const c = { x: el.clientWidth / 2, y: el.clientHeight / 2 }
    setDesl({ x: c.x - ((c.x - desl.x) * 1) / escala, y: c.y - ((c.y - desl.y) * 1) / escala })
    setEscala(1)
  }

  const baixo = (ev: React.MouseEvent) => {
    if (p.ferramenta) {
      const a = paraImagem(ev)
      setDesenho({ a, b: a })
    } else {
      arrasto.current = { x: ev.clientX, y: ev.clientY, dx: desl.x, dy: desl.y }
    }
  }
  const mover = (ev: React.MouseEvent) => {
    if (desenho) setDesenho({ ...desenho, b: paraImagem(ev) })
    else if (arrasto.current) {
      const a = arrasto.current
      setDesl({ x: a.dx + ev.clientX - a.x, y: a.dy + ev.clientY - a.y })
    }
  }
  const cima = () => {
    if (desenho) {
      const { a, b } = desenho
      if (Math.hypot(b.x - a.x, b.y - a.y) > 3) p.onDesenhado(a, b, r)
      setDesenho(null)
    }
    arrasto.current = null
  }

  if (!url) return <div className="visualizador vazio">Sem imagem retificada desta face.</div>

  return (
    <div className="visualizador-quadro">
      <div className="visualizador-barra">
        <span className="mono">{(escala * 100).toFixed(0)}%</span>
        <button type="button" onClick={umPraUm} title="Zoom 1:1 (necessário para microrriscos)">1:1</button>
        <button type="button" onClick={ajustar}>Ajustar</button>
        <span className="dica">{p.ferramenta ? `Desenhando ${p.ferramenta === 'linha' ? 'linha (risco)' : 'caixa'}: arraste sobre a imagem` : 'Roda: zoom · arraste: mover'}</span>
      </div>
      <div
        ref={caixa}
        className={`visualizador ${p.ferramenta ? 'desenhando' : ''}`}
        onWheel={roda}
        onMouseDown={baixo}
        onMouseMove={mover}
        onMouseUp={cima}
        onMouseLeave={cima}
        data-testid="visualizador"
      >
        <div style={{ transform: `translate(${desl.x}px, ${desl.y}px) scale(${escala})`, transformOrigin: '0 0', position: 'absolute' }}>
          <img
            src={url}
            alt={p.camadas[p.camadaAtiva]?.nome}
            draggable={false}
            onLoad={(e) => setTam({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
            style={{ display: 'block', imageRendering: escala >= 2 ? 'pixelated' : 'auto' }}
          />
          {tam && (
            <svg width={tam.w} height={tam.h} style={{ position: 'absolute', left: 0, top: 0 }}>
              {p.mostrarDefeitos && p.propostas.map((d) => (
                <Forma key={d.id} d={d} r={r} selecionado={p.selecionado === d.id} rejeitado={d.rejeitado} escala={escala}
                  onClick={() => p.onSelecionar(d.id)} />
              ))}
              {p.mostrarDefeitos && p.novos.map((d) => (
                <Forma key={d.chave} d={d} r={r} selecionado={p.selecionado === d.chave} rejeitado={false} escala={escala}
                  onClick={() => p.onSelecionar(d.chave)} novo />
              ))}
              {desenho && (p.ferramenta === 'linha'
                ? <line x1={desenho.a.x} y1={desenho.a.y} x2={desenho.b.x} y2={desenho.b.y} stroke="#F5C400" strokeWidth={2 / escala} />
                : <rect x={Math.min(desenho.a.x, desenho.b.x)} y={Math.min(desenho.a.y, desenho.b.y)}
                    width={Math.abs(desenho.b.x - desenho.a.x)} height={Math.abs(desenho.b.y - desenho.a.y)}
                    fill="none" stroke="#F5C400" strokeWidth={2 / escala} strokeDasharray={`${6 / escala}`} />)}
            </svg>
          )}
        </div>
      </div>
    </div>
  )
}

function Forma(p: { d: Defeito | DefeitoNovo; r: number; selecionado: boolean; rejeitado: boolean; escala: number; onClick: () => void; novo?: boolean }) {
  const cor = p.rejeitado ? '#6B7280' : CORES[p.d.tipo] ?? '#fff'
  const larg = (p.selecionado ? 3 : 1.5) / p.escala
  const tracejado = p.rejeitado ? `${4 / p.escala}` : p.novo ? `${2 / p.escala}` : undefined
  const [x, y, w, h] = p.d.caixa_mm.map((v) => v * p.r)
  const pts = p.d.geometria_mm?.pontos
  return (
    <g onMouseDown={(e) => { e.stopPropagation(); p.onClick() }} style={{ cursor: 'pointer' }}>
      {pts && pts.length > 1 && (
        <polyline points={pts.map(([px, py]) => `${px * p.r},${py * p.r}`).join(' ')} fill="none" stroke={cor}
          strokeWidth={larg * 1.5} strokeDasharray={tracejado} />
      )}
      <rect x={x - 3 / p.escala} y={y - 3 / p.escala} width={w + 6 / p.escala} height={h + 6 / p.escala} fill="transparent"
        stroke={cor} strokeWidth={larg} strokeDasharray={tracejado} />
    </g>
  )
}
