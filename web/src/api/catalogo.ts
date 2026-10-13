import { getApi } from './client'
export type Item = { id: string; nome: string }
export type Source = { source_url: string; fetched_at: string; expires_at: string; cache_hit: boolean }
export type Envelope<T> = { data: T; sources: Source[] }
export type Domains = { assuntos: Item[]; niveis: Item[]; periodos: Item[] }
export type Researches = { items: (Item & { agregados: Item[] })[]; pagination: { page: number; page_size: number; total_count: number; has_next: boolean } }
export type Metadata = Item & {
  sidra_url: string; pesquisa: string; assunto: string
  periodicidade: { frequencia: string; inicio: string; fim: string }
  niveis: { id: string; nome: string | null; grupo: string }[]
  variaveis: (Item & { unidade: string | null; sumarizacao: string[] })[]
  classificacoes: (Item & { sumarizacao: { status: boolean; excecao: string[] }; categorias: (Item & { unidade: string | null; nivel: number | null })[] })[]
  periodos: { id: string; literals: string[]; modificacao: string | null; ordem: number }[]
}
export const getDomains = (signal: AbortSignal) => getApi<Envelope<Domains>>('/dominios/', signal)
export const getResearches = (params: Record<string, string>, signal: AbortSignal) => getApi<Envelope<Researches>>('/pesquisas/', signal, params)
export const getMetadata = (id: string, signal: AbortSignal) => getApi<Envelope<Metadata>>(`/agregados/${id}/metadados/`, signal)
