// Defeitos da face: confirmar ou rejeitar, mudar tipo e zona; defeitos desenhados pelo técnico.
import { TIPOS, ZONAS, type Decisao, type Defeito, type DefeitoNovo, type TipoDefeito, type Zona } from '../tipos'
import { mm } from './regras'
import { CORES } from './cores'

interface Props {
  propostas: Defeito[]
  decisoes: Record<string, Decisao>
  novos: DefeitoNovo[]
  selecionado: string | null
  oculto: boolean
  onSelecionar: (id: string) => void
  onDecidir: (id: string, d: Decisao) => void
  onMudarNovo: (chave: string, mudanca: Partial<DefeitoNovo>) => void
  onRemoverNovo: (chave: string) => void
}

const medida = (d: { tipo: string; comprimento_mm: number | null; maior_dimensao_mm: number | null; area_mm2?: number | null }) =>
  d.tipo === 'risco' ? mm(d.comprimento_mm) : d.maior_dimensao_mm != null ? mm(d.maior_dimensao_mm) : d.area_mm2 != null ? `${d.area_mm2.toFixed(1).replace('.', ',')} mm²` : '—'

export function ListaDefeitos(p: Props) {
  return (
    <div className="lista-defeitos">
      <h3>Defeitos da face</h3>
      {p.oculto && <p className="aviso">Sessão cega: os defeitos da máquina aparecem depois que você salvar.</p>}
      {!p.oculto && p.propostas.length === 0 && <p className="vazio">A máquina não encontrou defeitos nesta face.</p>}
      <ul>
        {p.propostas.map((d) => {
          const dec = p.decisoes[d.id] ?? { estado: 'confirmado' }
          return (
            <li key={d.id} className={`${p.selecionado === d.id ? 'selecionado' : ''} ${dec.estado === 'rejeitado' ? 'rejeitado' : ''}`}
              onClick={() => p.onSelecionar(d.id)}>
              <span className="marcador" style={{ background: CORES[dec.tipo ?? d.tipo] }} />
              <select aria-label="Tipo" value={dec.tipo ?? d.tipo} onChange={(e) => p.onDecidir(d.id, { ...dec, tipo: e.target.value as TipoDefeito })}>
                {TIPOS.map((t) => <option key={t}>{t}</option>)}
              </select>
              <select aria-label="Zona" value={dec.zona ?? d.zona} onChange={(e) => p.onDecidir(d.id, { ...dec, zona: e.target.value as Zona })}>
                {ZONAS.map((z) => <option key={z}>{z}</option>)}
              </select>
              <span className="mono">{medida(d)}</span>
              <span className="tag">{d.visibilidade === 'visivel' ? 'visível' : 'só rasante'}</span>
              <button type="button" className={dec.estado === 'rejeitado' ? 'ativo' : ''} title="Rejeitar (X)"
                onClick={(e) => { e.stopPropagation(); p.onDecidir(d.id, { ...dec, estado: dec.estado === 'rejeitado' ? 'confirmado' : 'rejeitado' }) }}>
                {dec.estado === 'rejeitado' ? 'Rejeitado' : 'Rejeitar'}
              </button>
            </li>
          )
        })}
        {p.novos.map((d) => (
          <li key={d.chave} className={`novo ${p.selecionado === d.chave ? 'selecionado' : ''}`} onClick={() => p.onSelecionar(d.chave)}>
            <span className="marcador" style={{ background: CORES[d.tipo] }} />
            <select aria-label="Tipo do novo" value={d.tipo} onChange={(e) => p.onMudarNovo(d.chave, { tipo: e.target.value as TipoDefeito })}>
              {TIPOS.filter((t) => t !== 'anomalia').map((t) => <option key={t}>{t}</option>)}
            </select>
            <select aria-label="Zona do novo" value={d.zona} onChange={(e) => p.onMudarNovo(d.chave, { zona: e.target.value as Zona })}>
              {ZONAS.map((z) => <option key={z}>{z}</option>)}
            </select>
            <select aria-label="Visibilidade" value={d.visibilidade} onChange={(e) => p.onMudarNovo(d.chave, { visibilidade: e.target.value as DefeitoNovo['visibilidade'] })}>
              <option value="so_rasante">só rasante</option>
              <option value="visivel">visível</option>
            </select>
            <span className="mono">{medida({ ...d, area_mm2: null })}</span>
            <button type="button" onClick={(e) => { e.stopPropagation(); p.onRemoverNovo(d.chave) }}>Remover</button>
          </li>
        ))}
      </ul>
    </div>
  )
}
