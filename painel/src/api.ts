// Cliente da API do backend. STUB de autenticação: token do usuário guardado no navegador
// (trocar pela autenticação real do painel na integração).

const CHAVE_TOKEN = 'morecheck.token'

export function token(): string | null {
  try { return localStorage.getItem(CHAVE_TOKEN) } catch { return null }
}
export function guardarToken(t: string | null) {
  try { if (t) localStorage.setItem(CHAVE_TOKEN, t); else localStorage.removeItem(CHAVE_TOKEN) } catch { /* sem armazenamento */ }
}

export class ErroApi extends Error {
  status: number
  detalhe: unknown
  constructor(status: number, detalhe: unknown) {
    super(typeof detalhe === 'string' ? detalhe : (detalhe as { mensagem?: string })?.mensagem ?? `Erro ${status}`)
    this.status = status
    this.detalhe = detalhe
  }
}

export async function api<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  const r = await fetch(caminho, {
    ...opcoes,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token() ?? ''}`, ...(opcoes.headers ?? {}) },
  })
  if (!r.ok) {
    let detalhe: unknown = r.statusText
    try { detalhe = (await r.json()).detail } catch { /* corpo vazio */ }
    throw new ErroApi(r.status, detalhe)
  }
  return (r.status === 204 ? null : await r.json()) as T
}

export const post = <T>(caminho: string, corpo: unknown) => api<T>(caminho, { method: 'POST', body: JSON.stringify(corpo) })
export const put = <T>(caminho: string, corpo: unknown) => api<T>(caminho, { method: 'PUT', body: JSON.stringify(corpo) })
