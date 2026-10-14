import type { Envelope } from './api/catalogo'
import type { Draft, Result } from './api/consultas'

export const MAX_LINK = 2000
export const MAX_QUERY_BYTES = 65536
const invalid = () => { throw new Error('JSON de consulta inválido: confira versão, campos, tipos e IDs únicos.') }
function keys(value: unknown, expected: string[]): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).sort().join('|') === [...expected].sort().join('|')
}
const id = (v: unknown): v is string => typeof v === 'string' && /^[0-9]+$/.test(v)
const ids = (v: unknown) => Array.isArray(v) && v.length > 0 && v.every(id) && new Set(v).size === v.length
function rejectRepeatedKeys(text: string) {
  // JSON.parse checks syntax first; this token walk rejects ambiguous repeated keys,
  // including keys spelled with Unicode escapes, before returning a query.
  const stack: { keys: Set<string> | null; expectingKey: boolean }[] = []
  const tokens = text.match(/"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+/g) ?? []
  for (const token of tokens) {
    const current = stack.at(-1)
    if (token === '{' || token === '[') stack.push({ keys: token === '{' ? new Set() : null, expectingKey: token === '{' })
    else if (token === '}' || token === ']') stack.pop()
    else if (token === ',') { if (current?.keys) current.expectingKey = true }
    else if (token === ':') { if (current) current.expectingKey = false }
    else if (current?.keys && current.expectingKey && token.startsWith('"')) {
      const key: string = JSON.parse(token)
      if (current.keys.has(key)) invalid()
      current.keys.add(key); current.expectingKey = false
    }
  }
}
export function parseQuery(text: string): Draft {
  if (new TextEncoder().encode(text).length > MAX_QUERY_BYTES) return invalid()
  const value: unknown = JSON.parse(text)
  rejectRepeatedKeys(text)
  if (!keys(value, ['version', 'consulta']) || value.version !== 1) return invalid()
  const d = value.consulta
  if (!keys(d, ['agregado_id', 'nivel_id', 'variavel_ids', 'localidade_ids', 'periodo_ids', 'classificacoes'])) return invalid()
  if (!id(d.agregado_id) || typeof d.nivel_id !== 'string' || !/^N[0-9]+$/.test(d.nivel_id)) return invalid()
  if (![d.variavel_ids, d.localidade_ids, d.periodo_ids].every(ids) || !Array.isArray(d.classificacoes)) return invalid()
  const seen = new Set<string>()
  for (const c of d.classificacoes) {
    if (!keys(c, ['classificacao_id', 'categoria_ids']) || !id(c.classificacao_id) || !ids(c.categoria_ids) || seen.has(c.classificacao_id)) return invalid()
    seen.add(c.classificacao_id)
  }
  return d as Draft
}
export const queryJSON = (draft: Draft) => JSON.stringify({ version: 1, consulta: draft }, null, 2)
// JSON.stringify turns numeric -0 into 0; retain its sign in received JSON.
export function literalJSON(value: unknown): string {
  if (typeof value === 'number' && Object.is(value, -0)) return '-0'
  if (Array.isArray(value)) return '[' + value.map(literalJSON).join(',') + ']'
  if (value !== null && typeof value === 'object') return '{' + Object.entries(value).map(([key, v]) => JSON.stringify(key) + ':' + literalJSON(v)).join(',') + '}'
  return JSON.stringify(value)
}
export function queryLink(draft: Draft) {
  const url = new URL(window.location.href)
  url.hash = new URLSearchParams({ consulta: JSON.stringify({ version: 1, consulta: draft }) }).toString()
  return url.href.length <= MAX_LINK ? url.href : null
}
export function readLink(): Draft | null {
  const params = new URLSearchParams(window.location.hash.slice(1))
  if (!params.has('consulta')) return null
  if (params.size !== 1) return invalid()
  return parseQuery(params.get('consulta')!)
}
export function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = name; anchor.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
// Quote every cell; prefix potentially executable text before CSV escaping.
export function csvCell(value: unknown): string {
  let text = value === null || typeof value === 'object' || (typeof value === 'number' && Object.is(value, -0)) ? literalJSON(value) : String(value)
  if (/^[\s\u0000-\u001f]*[=+\-@]/u.test(text) || /^[\t\r\n]/.test(text)) text = `'${text}`
  return `"${text.replaceAll('"', '""')}"`
}
export function resultCSV(response: Envelope<Result>): string {
  const columns = ['agregado_id', 'variavel_id', 'variavel_nome', 'nivel_id', 'localidade_id', 'localidade_nome', 'periodo_id', 'classificacoes', 'unidade', 'unidade_original', 'unidade_status', 'valor_original', 'valor_original_tipo', 'valor_numerico', 'valor_status', 'origem_indice', 'consulta_aplicada', 'sources', 'normalizer_version']
  const rows = response.data.observacoes.map(row => {
    const values: Record<string, unknown> = { ...row, valor_original_tipo: row.valor_original === null ? 'null' : typeof row.valor_original, consulta_aplicada: response.data.consulta_aplicada, sources: response.sources, normalizer_version: response.data.normalizer_version }
    return columns.map(c => csvCell(values[c])).join(',')
  })
  return '\ufeff' + [columns.map(csvCell).join(','), ...rows].join('\r\n') + '\r\n'
}
