// Contratos do painel (guia 7.1 e 7.5).

export type Nota = 'A' | 'B' | 'C' | 'D'
export const NOTAS: Nota[] = ['A', 'B', 'C', 'D']
export const FACES = ['frente', 'traseira', 'lat_esq', 'lat_dir', 'topo', 'base'] as const
export type Face = (typeof FACES)[number]
export const NOMES_FACE: Record<Face, string> = {
  frente: 'Frente', traseira: 'Traseira', lat_esq: 'Lateral esq.', lat_dir: 'Lateral dir.', topo: 'Topo', base: 'Base',
}
export const TIPOS = ['risco', 'trinca', 'lascado', 'amassado', 'descascado', 'desgaste', 'mancha', 'anomalia'] as const
export type TipoDefeito = (typeof TIPOS)[number]
export const ZONAS = ['tela', 'recorte_tela', 'vidro_traseiro', 'ilha_camera', 'lente_camera', 'moldura', 'quina', 'botao', 'porta'] as const
export type Zona = (typeof ZONAS)[number]
export type Visibilidade = 'visivel' | 'so_rasante'
export type Luz = 'ambiente' | 'rasante_a' | 'rasante_b' | 'rasante_ab' | 'contraluz'

export interface Defeito {
  id: string
  face: Face
  tipo: TipoDefeito
  zona: Zona
  visibilidade: Visibilidade
  origem: 'maquina' | 'tecnico'
  estado: 'proposto' | 'confirmado' | 'rejeitado'
  caixa_mm: [number, number, number, number]
  geometria_mm: { tipo: 'polilinha' | 'poligono'; pontos: [number, number][] } | null
  comprimento_mm: number | null
  area_mm2: number | null
  maior_dimensao_mm: number | null
  confianca: number | null
  fonte: string
  foto_id: string | null
}

export interface FotoSessao {
  foto_id: string
  passo: number
  face: Face
  luz: Luz
  tentativa: number
  aceita: boolean | null
  qualidade: { ok: boolean; motivo?: string | null } | null
  faces_extraidas: Face[]
  original: string | null
  retificada: Partial<Record<Face, string>>
  anotada: Partial<Record<Face, string>>
}

export interface Sugestao {
  id: string
  nota_final: Nota
  notas_por_face: Record<Face, Nota>
  justificativas: Partial<Record<Face, string[]>>
  pendencias: string[]
  versao_visao: string
  versao_criterio: string
  tempo_ms: number
  margem_minima: number | null
}

export interface DetalheSessao {
  sessao_id: string
  status: string
  cega: boolean
  aparelho: {
    identificador: string; nome: string | null; cor: string | null
    dimensoes_mm: { largura: number; altura: number; espessura: number } | null
    zonas_mm: Record<string, Record<string, number[][]>>
    raio_canto_mm: number | null
  }
  px_por_mm_retificacao: number
  fotos: FotoSessao[]
  sugestao: Sugestao | null
  defeitos_propostos: Defeito[]
  avaliacoes: { id: string; nota_final: Nota; nota_regra: Nota; origem: string; justificativa: string | null; criada_em: string; notas_por_face: Record<Face, Nota>; substitui_id: string | null }[]
  defeitos_avaliacao: Defeito[]
  registro_id: string | null
}

export interface ItemFila {
  sessao_id: string; modelo: string | null; cor: string | null; iniciada_em: string; status: string; cega: boolean; sugestao_pronta: boolean
}

export interface ResultadoCriterio {
  nota_final: Nota
  notas_por_face: Record<Face, Nota>
  justificativas: Partial<Record<Face, string[]>>
  pendencias: string[]
  margem_minima: number | null
}

/** Defeito desenhado pelo técnico, ainda não salvo. */
export interface DefeitoNovo {
  chave: string
  face: Face
  tipo: TipoDefeito
  zona: Zona
  visibilidade: Visibilidade
  caixa_mm: [number, number, number, number]
  geometria_mm: { tipo: 'polilinha'; pontos: [number, number][] } | null
  comprimento_mm: number | null
  maior_dimensao_mm: number | null
  foto_id: string | null
}

export interface Decisao {
  estado: 'confirmado' | 'rejeitado'
  tipo?: TipoDefeito
  zona?: Zona
}
