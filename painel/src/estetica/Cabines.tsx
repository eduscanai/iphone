// Pareamento das cabines (D10): o admin gera um código de uso único (10 min) e o app da cabine lê o QR.
import QRCode from 'qrcode'
import { useCallback, useEffect, useState } from 'react'
import { api, post } from '../api'

interface Cabine { cabine_id: string; nome: string; ativa: boolean; criada_em: string; perfil_versao: number | null }

/** Conteúdo do QR: o app lê a URL da API e o código (Sources/Cabine/Pareamento.swift). */
export function conteudoQR(apiUrl: string, codigo: string) {
  return JSON.stringify({ api: apiUrl, codigo })
}

export function Cabines() {
  const [cabines, setCabines] = useState<Cabine[] | null>(null)
  const [codigo, setCodigo] = useState<{ codigo: string; expira_em: string; qr: string } | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const apiUrl = window.location.origin  // em produção, painel e API no mesmo domínio; ajustar se não

  const listar = useCallback(() => api<Cabine[]>('/cabines').then(setCabines).catch((e) => setErro(e.message)), [])
  useEffect(() => { listar() }, [listar])

  const parear = async () => {
    try {
      const r = await post<{ codigo: string; expira_em: string }>('/cabines/pareamento', {})
      setCodigo({ ...r, qr: await QRCode.toDataURL(conteudoQR(apiUrl, r.codigo), { margin: 1, width: 240 }) })
    } catch (e) { setErro((e as Error).message) }
  }
  const revogar = async (id: string) => {
    if (!confirm('Revogar esta cabine? Ela para de enviar fotos até ser pareada de novo.')) return
    await post(`/cabines/${id}/revogar`, {})
    listar()
  }

  return (
    <section className="config">
      <h3>Cabines</h3>
      {erro && <p className="erro">{erro}</p>}
      <ul className="por-face">
        {(cabines ?? []).map((c) => (
          <li key={c.cabine_id}>
            <b>{c.nome}</b> · {c.ativa ? 'ativa' : 'revogada'} · perfil {c.perfil_versao ?? '—'}{' '}
            {c.ativa && <button type="button" className="link" onClick={() => revogar(c.cabine_id)}>revogar</button>}
          </li>
        ))}
      </ul>
      <button type="button" onClick={parear}>Parear nova cabine</button>
      {codigo && (
        <div className="pareamento">
          <img src={codigo.qr} alt="QR de pareamento" />
          <p>Código <b className="mono">{codigo.codigo}</b> · vale até {new Date(codigo.expira_em).toLocaleTimeString('pt-BR')}</p>
          <p className="pequeno">No iPhone da cabine: Modo Cabine → Parear → leia o QR ou digite o código.</p>
        </div>
      )}
    </section>
  )
}
