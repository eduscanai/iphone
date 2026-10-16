// Relatório de concordância máquina × técnico (guia 11.3) e configuração da loja (gate, 13.1).
import { useCallback, useEffect, useState } from 'react'
import { api, ErroApi, put } from '../api'
import { FACES, NOMES_FACE, NOTAS } from '../tipos'
import { Cabines } from './Cabines'
import { pct } from './regras'

interface Metricas {
  n: number; exata?: number; mais_menos_1?: number; a_2_ou_mais?: number; kappa_quadratico?: number | null
  kappa_ic95?: [number, number] | null; recall?: Record<string, number | null>
  matriz?: { valores: number[][] }; limite_superior_erro_2_notas?: number
}
interface Relatorio {
  geral: Metricas
  por_face: Record<string, Metricas>
  evolucao_semanal: { semana: string; n: number; exata: number }[]
  discordantes: { sessao_id: string; maquina: string; tecnico: string; modelo: string | null; distancia: number }[]
  gate: { passou: boolean; motivos: string[]; observacao: string }
  aviso: string | null
}
interface ConfigLoja { modo: string; percentual_cego: number; sombra_iniciada_em: string | null; ultimo_aviso: { quando: string; motivos: string[] } | null; fila_parada: boolean }

const kappa = (k?: number | null) => (k == null ? '—' : k.toFixed(3).replace('.', ','))

const MODOS: [string, string][] = [['desligado', 'Desligado'], ['assistido', 'Assistido'], ['automatico', 'Automático']]

export function RelatorioConcordancia({ onAbrir, admin }: { onAbrir: (id: string) => void; admin: boolean }) {
  const [filtros, setFiltros] = useState({ de: '', ate: '', modelo: '', face: '', tecnico: '', incluir_nao_cegas: false })
  const [rel, setRel] = useState<Relatorio | null>(null)
  const [cfg, setCfg] = useState<ConfigLoja | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [msgCfg, setMsgCfg] = useState<string | null>(null)

  const buscar = useCallback(async () => {
    const q = new URLSearchParams()
    Object.entries(filtros).forEach(([k, v]) => { if (v) q.set(k, String(v)) })
    try {
      setRel(await api<Relatorio>(`/estetica/concordancia?${q}`))
      setCfg(await api<ConfigLoja>('/estetica/config'))
    } catch (e) { setErro((e as Error).message) }
  }, [filtros])
  useEffect(() => { buscar() }, [buscar])

  const gravar = async (modo: string, percentual_cego: number) => {
    setMsgCfg(null)
    try {
      await put('/estetica/config', { modo, percentual_cego })
      setMsgCfg('Configuração salva.')
      buscar()
    } catch (e) {
      const det = e instanceof ErroApi ? (e.detalhe as { motivos?: string[] }) : null
      setMsgCfg(det?.motivos ? `Gate não atendido: ${det.motivos.join('; ')}` : (e as Error).message)
    }
  }

  const g = rel?.geral
  return (
    <div className="relatorio">
      <h2>Concordância máquina × técnico</h2>
      <form className="filtros" onSubmit={(e) => { e.preventDefault(); buscar() }}>
        <label>De <input type="date" value={filtros.de} onChange={(e) => setFiltros({ ...filtros, de: e.target.value })} /></label>
        <label>Até <input type="date" value={filtros.ate} onChange={(e) => setFiltros({ ...filtros, ate: e.target.value })} /></label>
        <label>Modelo <input placeholder="iPhone14,5" value={filtros.modelo} onChange={(e) => setFiltros({ ...filtros, modelo: e.target.value })} /></label>
        <label>Face <select value={filtros.face} onChange={(e) => setFiltros({ ...filtros, face: e.target.value })}>
          <option value="">nota final</option>{FACES.map((f) => <option key={f} value={f}>{NOMES_FACE[f]}</option>)}</select></label>
        <label className="checar"><input type="checkbox" checked={filtros.incluir_nao_cegas}
          onChange={(e) => setFiltros({ ...filtros, incluir_nao_cegas: e.target.checked })} /> incluir sessões não cegas</label>
      </form>
      {rel?.aviso && <p className="aviso">{rel.aviso}</p>}
      {erro && <p className="erro">Erro: {erro}</p>}
      {g && g.n === 0 && <p className="vazio">Ainda não há avaliações cegas com sugestão no período.</p>}
      {g && g.n > 0 && (
        <>
          <div className="indicadores">
            <Indicador rotulo="Aparelhos" valor={String(g.n)} />
            <Indicador rotulo="Concordância exata" valor={pct(g.exata)} meta="≥ 90%" ok={(g.exata ?? 0) >= 0.9} />
            <Indicador rotulo="± 1 nota" valor={pct(g.mais_menos_1)} />
            <Indicador rotulo="A 2+ notas" valor={String(g.a_2_ou_mais)} meta="0" ok={g.a_2_ou_mais === 0} />
            <Indicador rotulo="Kappa ponderado" valor={kappa(g.kappa_quadratico)}
              detalhe={g.kappa_ic95 ? `IC 95%: ${kappa(g.kappa_ic95[0])}–${kappa(g.kappa_ic95[1])}` : undefined} />
          </div>
          <div className="duas-colunas">
            <div>
              <h3>Matriz de confusão (linhas: técnico; colunas: máquina)</h3>
              <table className="matriz"><thead><tr><th />{NOTAS.map((n) => <th key={n}>{n}</th>)}<th>Recall</th></tr></thead>
                <tbody>{NOTAS.map((n, i) => (
                  <tr key={n}><th>{n}</th>{g.matriz!.valores[i].map((v, j) => <td key={j} className={i === j ? 'diagonal' : v ? 'erro-celula' : ''}>{v}</td>)}
                    <td className={(g.recall?.[n] ?? 1) < 0.8 ? 'abaixo' : ''}>{pct(g.recall?.[n])}</td></tr>))}</tbody></table>
            </div>
            <div>
              <h3>Evolução semanal</h3>
              <ul className="semanas">{rel!.evolucao_semanal.map((s) => (
                <li key={s.semana}><span className="mono">{s.semana}</span><span className="barra"><span style={{ width: `${s.exata * 100}%` }} /></span>
                  <span className="mono">{pct(s.exata)} · {s.n}</span></li>))}</ul>
              <h3>Por face</h3>
              <ul className="por-face">{FACES.map((f) => <li key={f}>{NOMES_FACE[f]}: <b>{pct(rel!.por_face[f]?.exata)}</b></li>)}</ul>
            </div>
          </div>
          <h3>Casos discordantes</h3>
          <table className="discordantes"><thead><tr><th>Sessão</th><th>Modelo</th><th>Máquina</th><th>Técnico</th><th>Distância</th></tr></thead>
            <tbody>{rel!.discordantes.map((c) => (
              <tr key={c.sessao_id} onClick={() => onAbrir(c.sessao_id)}><td className="mono">{c.sessao_id.slice(0, 8)}</td><td>{c.modelo}</td>
                <td>{c.maquina}</td><td>{c.tecnico}</td><td className={c.distancia >= 2 ? 'abaixo' : ''}>{c.distancia}</td></tr>))}</tbody></table>
        </>
      )}
      {rel && (
        <section className={`gate ${rel.gate.passou ? 'passou' : ''}`}>
          <h3>Gate do modo automático: {rel.gate.passou ? 'atendido' : 'não atendido'}</h3>
          <ul>{rel.gate.motivos.map((m) => <li key={m}>{m}</li>)}</ul>
          <p className="pequeno">{rel.gate.observacao} Medido só em sessões cegas de aparelhos do conjunto de teste.</p>
        </section>
      )}
      {cfg && (
        <section className="config">
          <h3>Configuração da loja</h3>
          {cfg.fila_parada && <p className="erro">Fila de visão parada há mais de 5 minutos: confira o worker.</p>}
          {cfg.ultimo_aviso && <p className="aviso">Automático desligado em {new Date(cfg.ultimo_aviso.quando).toLocaleString('pt-BR')}: {cfg.ultimo_aviso.motivos.join('; ')}</p>}
          <div className="linha">
            {MODOS.map(([m, rotulo]) => (
              <button key={m} type="button" className={cfg.modo === m ? 'ativa' : ''} disabled={!admin}
                onClick={() => gravar(m, cfg.percentual_cego)}>{rotulo}</button>
            ))}
            <label>Amostra cega <input type="number" min={0} max={100} defaultValue={cfg.percentual_cego} disabled={!admin}
              onBlur={(e) => Number(e.target.value) !== cfg.percentual_cego && gravar(cfg.modo, Number(e.target.value))} /> %</label>
          </div>
          {!admin && <p className="pequeno">Só o administrador da loja muda a configuração.</p>}
          <p className="pequeno">Modo sombra (100% cego) {cfg.sombra_iniciada_em ? `desde ${new Date(cfg.sombra_iniciada_em).toLocaleDateString('pt-BR')}` : 'não iniciado'}. Ligar o automático é decisão do responsável.</p>
          {msgCfg && <p role="status">{msgCfg}</p>}
        </section>
      )}
      {admin && <Cabines />}
    </div>
  )
}

function Indicador(p: { rotulo: string; valor: string; meta?: string; ok?: boolean; detalhe?: string }) {
  return (
    <div className={`indicador ${p.ok === false ? 'abaixo' : ''}`}>
      <span className="rotulo">{p.rotulo}</span>
      <span className="valor">{p.valor}</span>
      {p.meta && <span className="meta">meta {p.meta}</span>}
      {p.detalhe && <span className="meta">{p.detalhe}</span>}
    </div>
  )
}
