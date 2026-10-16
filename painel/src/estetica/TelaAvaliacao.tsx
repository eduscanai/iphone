// Tela de avaliação (guia 11.2): o técnico confirma ou corrige a sugestão em < 30 s.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, ErroApi, post } from '../api'
import {
  FACES, NOMES_FACE, type Decisao, type DefeitoNovo, type DetalheSessao, type Face, type FotoSessao, type Nota,
  type ResultadoCriterio,
} from '../tipos'
import { ListaDefeitos } from './ListaDefeitos'
import { acaoDaTecla, caixaParaMm, dimsFace, linhaParaMm, notaFinal, type Ponto } from './regras'
import { SeletorNota } from './SeletorNota'
import { VisualizadorFace, type Camada, type Ferramenta } from './VisualizadorFace'

const ORDEM_LUZ = ['ambiente', 'rasante_a', 'rasante_b', 'rasante_ab', 'contraluz']
const NOMES_LUZ: Record<string, string> = {
  ambiente: 'Ambiente', rasante_a: 'Rasante A', rasante_b: 'Rasante B', rasante_ab: 'Rasante A+B', contraluz: 'Contraluz',
}
const TODAS_A = Object.fromEntries(FACES.map((f) => [f, 'A'])) as Record<Face, Nota>

function camadasDaFace(fotos: FotoSessao[], face: Face): (Camada & { foto_id: string })[] {
  const ultima = new Map<string, FotoSessao>()
  for (const f of fotos) if (f.retificada[face]) ultima.set(f.luz, f)
  return ORDEM_LUZ.filter((l) => ultima.has(l)).map((l) => {
    const f = ultima.get(l)!
    return { nome: NOMES_LUZ[l], url: f.retificada[face]!, foto_id: f.foto_id }
  })
}

const zonaPadrao = (face: Face) => (face === 'frente' ? 'tela' : face === 'traseira' ? 'vidro_traseiro' : 'moldura')

export function TelaAvaliacao({ sessaoId, onVoltar }: { sessaoId: string; onVoltar: () => void }) {
  const [d, setD] = useState<DetalheSessao | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [face, setFace] = useState<Face>('frente')
  const [camada, setCamada] = useState(0)
  const [mostrarDefeitos, setMostrarDefeitos] = useState(true)
  const [decisoes, setDecisoes] = useState<Record<string, Decisao>>({})
  const [novos, setNovos] = useState<DefeitoNovo[]>([])
  const [notas, setNotas] = useState<Record<Face, Nota>>(TODAS_A)
  const manuais = useRef(new Set<Face>())
  const [finalManual, setFinalManual] = useState<Nota | null>(null)
  const [justificativa, setJustificativa] = useState('')
  const [regra, setRegra] = useState<ResultadoCriterio | null>(null)
  const [ferramenta, setFerramenta] = useState<Ferramenta>(null)
  const [selecionado, setSelecionado] = useState<string | null>(null)
  const [salvando, setSalvando] = useState(false)
  const [mensagem, setMensagem] = useState<string | null>(null)

  const carregar = useCallback(async () => {
    try {
      const det = await api<DetalheSessao>(`/estetica/sessoes/${sessaoId}`)
      setD(det)
      setNotas(det.sugestao?.notas_por_face ?? TODAS_A)
      manuais.current.clear()
      setDecisoes({}); setNovos([]); setFinalManual(null); setJustificativa('')
    } catch (e) {
      setErro((e as Error).message)
    }
  }, [sessaoId])
  useEffect(() => { carregar() }, [carregar])

  const oculto = !!d && d.cega && d.avaliacoes.length === 0
  const propostas = useMemo(() => (oculto ? [] : d?.defeitos_propostos ?? []), [d, oculto])

  // Defeitos que entram na regra: propostas não rejeitadas (com as mudanças) + desenhados
  const ativos = useMemo(() => [
    ...propostas.filter((p) => decisoes[p.id]?.estado !== 'rejeitado').map((p) => ({
      face: p.face, tipo: decisoes[p.id]?.tipo ?? p.tipo, zona: decisoes[p.id]?.zona ?? p.zona, visibilidade: p.visibilidade,
      comprimento_mm: p.comprimento_mm, area_mm2: p.area_mm2, maior_dimensao_mm: p.maior_dimensao_mm,
    })),
    ...novos.map((n) => ({ face: n.face, tipo: n.tipo, zona: n.zona, visibilidade: n.visibilidade,
      comprimento_mm: n.comprimento_mm, area_mm2: null, maior_dimensao_mm: n.maior_dimensao_mm })),
  ], [propostas, decisoes, novos])

  useEffect(() => {
    if (!d) return
    const t = setTimeout(async () => {
      try {
        const r = await post<ResultadoCriterio>('/estetica/criterio/avaliar', { defeitos: ativos })
        setRegra(r)
        setNotas((atual) => {
          const n = { ...atual }
          for (const f of FACES) if (!manuais.current.has(f)) n[f] = r.notas_por_face[f]
          return n
        })
      } catch (e) {
        setErro((e as Error).message)
      }
    }, 120)
    return () => clearTimeout(t)
  }, [ativos, d])

  const camadas = useMemo(() => (d ? camadasDaFace(d.fotos, face) : []), [d, face])
  const notaCalculada = notaFinal(notas)
  const final = finalManual ?? notaCalculada
  const precisaJustificar = !!regra && final !== regra.nota_final
  const podeSalvar = !!d?.registro_id && !!regra && (!precisaJustificar || justificativa.trim().length > 0) && !salvando

  const mudarNotaFace = (f: Face, n: Nota) => {
    manuais.current.add(f)
    setNotas((a) => ({ ...a, [f]: n }))
  }

  const salvar = useCallback(async () => {
    if (!d || !podeSalvar) return
    setSalvando(true); setMensagem(null)
    try {
      const vigente = d.avaliacoes.filter((a) => !d.avaliacoes.some((b) => b.substitui_id === a.id)).at(-1)
      await post(`/registros/${d.registro_id}/estetica`, {
        sessao_id: d.sessao_id,
        notas_por_face: notas,
        nota_final: final,
        defeitos: [
          ...propostas.map((p) => ({ proposta_id: p.id, estado: decisoes[p.id]?.estado ?? 'confirmado',
            ...(decisoes[p.id]?.tipo ? { tipo: decisoes[p.id].tipo } : {}), ...(decisoes[p.id]?.zona ? { zona: decisoes[p.id].zona } : {}) })),
          ...novos.map(({ chave: _c, ...n }) => ({ novo: n })), // eslint-disable-line @typescript-eslint/no-unused-vars
        ],
        justificativa: precisaJustificar ? justificativa.trim() : null,
        substitui_id: vigente?.id ?? null,
      })
      setMensagem(oculto ? 'Avaliação salva. Agora você pode comparar com a sugestão da máquina.' : 'Avaliação salva.')
      await carregar()
    } catch (e) {
      setMensagem(e instanceof ErroApi ? `Erro: ${e.message}` : String(e))
    } finally {
      setSalvando(false)
    }
  }, [d, podeSalvar, notas, final, propostas, decisoes, novos, precisaJustificar, justificativa, oculto, carregar])

  const desenhado = (a: Ponto, b: Ponto, r: number) => {
    const chave = `novo-${Date.now()}`
    const foto_id = (camadas[camada] as { foto_id?: string } | undefined)?.foto_id ?? null
    if (ferramenta === 'linha') {
      const l = linhaParaMm(a, b, r)
      setNovos((n) => [...n, { chave, face, tipo: 'risco', zona: zonaPadrao(face), visibilidade: 'so_rasante', caixa_mm: l.caixa,
        geometria_mm: { tipo: 'polilinha', pontos: l.pontos }, comprimento_mm: l.comprimento, maior_dimensao_mm: l.comprimento, foto_id }])
    } else {
      const c = caixaParaMm(a, b, r)
      setNovos((n) => [...n, { chave, face, tipo: face === 'frente' || face === 'traseira' ? 'lascado' : 'amassado',
        zona: zonaPadrao(face), visibilidade: 'visivel', caixa_mm: c, geometria_mm: null, comprimento_mm: null,
        maior_dimensao_mm: Math.max(c[2], c[3]), foto_id }])
    }
    setSelecionado(chave)
    setFerramenta(null)
  }

  // Atalhos (guia 11.2): 1–6 face · A–D nota da face · espaço camada · X rejeita · N desenha · Enter salva
  useEffect(() => {
    const tecla = (ev: KeyboardEvent) => {
      const alvo = ev.target as HTMLElement
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(alvo.tagName)) return
      const a = acaoDaTecla(ev.key)
      if (!a) return
      ev.preventDefault()
      if (a.tipo === 'face') { setFace(a.face); setCamada(0) }
      else if (a.tipo === 'nota') mudarNotaFace(face, a.nota)
      else if (a.tipo === 'camada') setCamada((c) => (camadas.length ? (c + 1) % camadas.length : 0))
      else if (a.tipo === 'rejeitar' && selecionado && propostas.some((p) => p.id === selecionado)) {
        setDecisoes((x) => ({ ...x, [selecionado]: { ...(x[selecionado] ?? {}), estado: x[selecionado]?.estado === 'rejeitado' ? 'confirmado' : 'rejeitado' } }))
      } else if (a.tipo === 'desenhar') setFerramenta((f) => (f ? null : 'linha'))
      else if (a.tipo === 'salvar') salvar()
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  }, [face, camadas.length, selecionado, propostas, salvar])

  if (erro) return <div className="erro">Erro: {erro} <button onClick={onVoltar}>Voltar</button></div>
  if (!d) return <div className="carregando">Carregando…</div>
  const dims = d.aparelho.dimensoes_mm
  const larguraMm = dims ? dimsFace(face, dims)[0] : 1
  const daFace = propostas.filter((p) => p.face === face)
  const novosDaFace = novos.filter((n) => n.face === face)
  const ultima = d.avaliacoes.at(-1)

  return (
    <div className="tela-avaliacao">
      <header className="cabecalho">
        <button type="button" className="voltar" onClick={onVoltar}>← Fila</button>
        <h1>{d.aparelho.nome ?? d.aparelho.identificador} <small>{d.aparelho.cor}</small></h1>
        {d.cega && <span className="selo-cega">cega</span>}
        <span className="status">{d.status.replace('_', ' ')}</span>
      </header>

      <aside className="faces">
        {FACES.map((f, i) => {
          const mini = camadasDaFace(d.fotos, f)[0]?.url
          return (
            <button key={f} type="button" className={`face ${f === face ? 'ativa' : ''}`} onClick={() => { setFace(f); setCamada(0) }}>
              <span className="tecla">{i + 1}</span>
              {mini ? <img src={mini} alt="" /> : <span className="sem-foto">sem foto</span>}
              <span className="nome">{NOMES_FACE[f]}</span>
              <span className={`nota-face nota-${notas[f]}`}>{notas[f]}</span>
            </button>
          )
        })}
      </aside>

      <main className="centro">
        <div className="camadas" role="group" aria-label="Camadas">
          {camadas.map((c, i) => (
            <button key={c.nome} type="button" className={i === camada ? 'ativa' : ''} onClick={() => setCamada(i)}>{c.nome}</button>
          ))}
          <label><input type="checkbox" checked={mostrarDefeitos} onChange={(e) => setMostrarDefeitos(e.target.checked)} /> Defeitos</label>
          <button type="button" disabled title="Disponível quando o PatchCore estiver ativo (fase 4)">Mapa de anomalia</button>
          <span className="separador" />
          <button type="button" className={ferramenta === 'linha' ? 'ativa' : ''} onClick={() => setFerramenta(ferramenta === 'linha' ? null : 'linha')}>Linha (risco) · N</button>
          <button type="button" className={ferramenta === 'caixa' ? 'ativa' : ''} onClick={() => setFerramenta(ferramenta === 'caixa' ? null : 'caixa')}>Caixa</button>
        </div>
        <VisualizadorFace key={face} camadas={camadas} camadaAtiva={camada} mostrarDefeitos={mostrarDefeitos}
          propostas={daFace.map((p) => ({ ...p, tipo: decisoes[p.id]?.tipo ?? p.tipo, rejeitado: decisoes[p.id]?.estado === 'rejeitado' }))}
          novos={novosDaFace} selecionado={selecionado} ferramenta={ferramenta} larguraMm={larguraMm}
          onSelecionar={setSelecionado} onDesenhado={desenhado} />
      </main>

      <section className="painel-direito">
        <ListaDefeitos propostas={daFace} decisoes={decisoes} novos={novosDaFace} selecionado={selecionado} oculto={oculto}
          onSelecionar={setSelecionado} onDecidir={(id, dec) => setDecisoes((x) => ({ ...x, [id]: dec }))}
          onMudarNovo={(chave, m) => setNovos((n) => n.map((x) => (x.chave === chave ? { ...x, ...m } : x)))}
          onRemoverNovo={(chave) => setNovos((n) => n.filter((x) => x.chave !== chave))} />

        <SeletorNota rotulo={`Nota da face (${NOMES_FACE[face]})`} valor={notas[face]} regra={regra?.notas_por_face[face] ?? null}
          onMudar={(n) => mudarNotaFace(face, n)} teclas />
        {(regra?.justificativas[face] ?? []).map((j) => <p key={j} className="justificativa-regra">{j}</p>)}

        <div className="nota-final">
          <SeletorNota rotulo="Nota final" valor={final} regra={regra?.nota_final ?? null} onMudar={setFinalManual} />
          {finalManual && <button type="button" className="link" onClick={() => setFinalManual(null)}>usar pior face ({notaCalculada})</button>}
        </div>
        {precisaJustificar && (
          <label className="justificativa">
            Justificativa (obrigatória: sua nota difere da regra)
            <textarea value={justificativa} onChange={(e) => setJustificativa(e.target.value)} rows={3} />
          </label>
        )}
        {!oculto && d.sugestao && (
          <div className="sugestao">
            <h3>Sugestão da máquina: <span className={`nota-face nota-${d.sugestao.nota_final}`}>{d.sugestao.nota_final}</span></h3>
            {d.sugestao.pendencias.length > 0 && <ul className="pendencias">{d.sugestao.pendencias.map((p) => <li key={p}>{p}</li>)}</ul>}
            <p className="mono pequeno">critério {d.sugestao.versao_criterio} · visão {d.sugestao.versao_visao} · {(d.sugestao.tempo_ms / 1000).toFixed(1)} s</p>
          </div>
        )}
        {ultima && <p className="ultima">Última avaliação: <b>{ultima.nota_final}</b> ({ultima.origem}) — salvar de novo cria uma correção.</p>}
        {!d.registro_id && <p className="aviso">Sessão sem registro (laudo): não dá para salvar.</p>}
        <button type="button" className="salvar" disabled={!podeSalvar} onClick={salvar}>{salvando ? 'Salvando…' : 'Salvar · Enter'}</button>
        {mensagem && <p className="mensagem" role="status">{mensagem}</p>}
      </section>
    </div>
  )
}
