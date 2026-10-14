import { getApi } from './client'
import type { Envelope, Metadata, Researches } from './catalogo'
export type Draft = { agregado_id: string; nivel_id: string; variavel_ids: string[]; localidade_ids: string[]; periodo_ids: string[]; classificacoes: { classificacao_id: string; categoria_ids: string[] }[] }
export type Validated = { consulta_resolvida: Draft; source_url: string; estimated_observations: number; limites: Record<string, number>; warnings: unknown[] }
export type Locality = { id: string; nome: string; nivel_id: string; uf_sigla: null }
export const getPeriods = (id: string, signal: AbortSignal) => getApi<Envelope<{ items: Metadata['periodos'] }>>(`/agregados/${id}/periodos/`, signal)
export const getLocations = (id: string, params: Record<string, string>, signal: AbortSignal) => getApi<Envelope<{ items: Locality[]; pagination: Researches['pagination'] }>>(`/agregados/${id}/localidades/`, signal, params)
export const validateDraft = (draft: Draft, signal: AbortSignal) => getApi<Envelope<Validated>>('/consultas/validar/', signal, undefined, draft)
