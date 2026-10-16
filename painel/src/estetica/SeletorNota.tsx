import { NOTAS, type Nota } from '../tipos'

export function SeletorNota(p: { rotulo: string; valor: Nota; regra: Nota | null; onMudar: (n: Nota) => void; teclas?: boolean }) {
  return (
    <div className="seletor-nota" role="group" aria-label={p.rotulo}>
      <span className="rotulo">{p.rotulo}</span>
      {NOTAS.map((n) => (
        <button key={n} type="button" className={`nota nota-${n} ${p.valor === n ? 'ativa' : ''}`} aria-pressed={p.valor === n}
          onClick={() => p.onMudar(n)} title={p.teclas ? `Tecla ${n}` : undefined}>{n}</button>
      ))}
      {p.regra && <span className={`regra ${p.regra !== p.valor ? 'diferente' : ''}`}>pela regra: <b>{p.regra}</b></span>}
    </div>
  )
}
