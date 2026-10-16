import { useEffect, useState } from 'react'
import { api } from '../api'
import type { ItemFila } from '../tipos'

export function FilaAvaliacao({ onAbrir }: { onAbrir: (id: string) => void }) {
  const [itens, setItens] = useState<ItemFila[] | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  useEffect(() => {
    let vivo = true
    const buscar = () => api<ItemFila[]>('/estetica/fila?status=aguardando_tecnico')
      .then((x) => vivo && setItens(x)).catch((e) => vivo && setErro(e.message))
    buscar()
    const t = setInterval(buscar, 5000)
    return () => { vivo = false; clearInterval(t) }
  }, [])
  if (erro) return <p className="erro">Erro: {erro}</p>
  if (!itens) return <p className="carregando">Carregando…</p>
  return (
    <div className="fila">
      <h2>Aguardando técnico <span className="contador">{itens.length}</span></h2>
      {itens.length === 0 && <p className="vazio">Nenhuma sessão esperando avaliação.</p>}
      <table>
        <thead><tr><th>Aparelho</th><th>Cor</th><th>Início</th><th>Sugestão</th><th /></tr></thead>
        <tbody>
          {itens.map((i) => (
            <tr key={i.sessao_id} onClick={() => onAbrir(i.sessao_id)} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onAbrir(i.sessao_id)}>
              <td>{i.modelo}</td>
              <td>{i.cor ?? '—'}</td>
              <td className="mono">{new Date(i.iniciada_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</td>
              <td>{i.sugestao_pronta ? 'pronta' : 'processando'}</td>
              <td>{i.cega && <span className="selo-cega">cega</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
