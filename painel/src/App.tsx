import { useEffect, useState } from 'react'
import { api, guardarToken, token } from './api'
import { FilaAvaliacao } from './estetica/FilaAvaliacao'
import { RelatorioConcordancia } from './estetica/RelatorioConcordancia'
import { TelaAvaliacao } from './estetica/TelaAvaliacao'

function rota() {
  return window.location.hash.replace(/^#\/?/, '').split('/')
}

export default function App() {
  const [partes, setPartes] = useState(rota())
  const [tem, setTem] = useState(!!token())
  const [eu, setEu] = useState<{ nome: string; papel: string } | null>(null)
  useEffect(() => {
    if (!tem) return
    api<{ nome: string; papel: string }>('/estetica/eu').then(setEu).catch(() => { guardarToken(null); setTem(false) })
  }, [tem])
  useEffect(() => {
    const f = () => setPartes(rota())
    window.addEventListener('hashchange', f)
    return () => window.removeEventListener('hashchange', f)
  }, [])
  const ir = (h: string) => { window.location.hash = h }

  if (!tem) return <Entrar onEntrar={() => setTem(true)} />
  const [pagina, id] = partes
  return (
    <div className="app">
      <nav className="topo">
        <span className="marca">morecheck <b>estética</b></span>
        <a href="#/fila" className={pagina !== 'concordancia' ? 'ativo' : ''}>Avaliação</a>
        <a href="#/concordancia" className={pagina === 'concordancia' ? 'ativo' : ''}>Concordância</a>
        {eu && <span className="usuario">{eu.nome}{eu.papel === 'admin' ? ' · admin' : ''}</span>}
        <button type="button" className="sair" onClick={() => { guardarToken(null); setTem(false) }}>Sair</button>
      </nav>
      {pagina === 'sessao' && id ? <TelaAvaliacao sessaoId={id} onVoltar={() => ir('/fila')} />
        : pagina === 'concordancia' ? <RelatorioConcordancia admin={eu?.papel === 'admin'} onAbrir={(s) => ir(`/sessao/${s}`)} />
        : <FilaAvaliacao onAbrir={(s) => ir(`/sessao/${s}`)} />}
    </div>
  )
}

function Entrar({ onEntrar }: { onEntrar: () => void }) {
  const [t, setT] = useState('')
  return (
    <form className="entrar" onSubmit={(e) => { e.preventDefault(); guardarToken(t.trim()); onEntrar() }}>
      <span className="marca">morecheck <b>estética</b></span>
      <label>Token de acesso <input value={t} onChange={(e) => setT(e.target.value)} autoFocus /></label>
      <button type="submit" disabled={!t.trim()}>Entrar</button>
      <p className="pequeno">Desenvolvimento: use o token do técnico de <code>python -m app.dev semear</code>.</p>
    </form>
  )
}
