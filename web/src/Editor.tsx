import { useEffect, useRef, useState } from 'react'
import { QueryShare } from './Sharing'
import { useQuery } from '@tanstack/react-query'
import type { Envelope, Item, Metadata } from './api/catalogo'
import { executeDraft, getLocations, getPeriods, validateDraft, type Draft, type Result } from './api/consultas'

export type ExecutionProps = { initialDraft?: Draft; onResult: (value: Envelope<Result>) => void; onDraftChange: (draft?: Draft) => void }

function Multi({ label, items, values, change }: { label: string; items: Item[]; values: string[]; change: (values: string[]) => void }) {
  const [search, setSearch] = useState('')
  const visible = items.filter(v => `${v.id} ${v.nome}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
  return <fieldset><legend>{label}</legend><input aria-label={`Buscar ${label}`} placeholder="Código ou nome" value={search} onChange={e => setSearch(e.target.value)} />
    {visible.length === 0 && <p role="status">Nenhum item encontrado em {label}.</p>}
    <div className="choices">{visible.map(v => <label key={v.id}><input type="checkbox" checked={values.includes(v.id)} onChange={e => change(e.target.checked ? [...values, v.id] : values.filter(id => id !== v.id))} />{v.id} · {v.nome}</label>)}</div>
  </fieldset>
}

function QueryFeedback({ query }: { query: { isFetching: boolean; error: Error | null; refetch: () => unknown } }) {
  if (query.error) return <p role="alert">{query.error.message} <button onClick={() => void query.refetch()}>Tentar novamente</button></p>
  return query.isFetching ? <p role="status">Carregando dimensões…</p> : null
}

export default function Editor({ metadata, level, setLevel, onResult, onDraftChange, initialDraft }: { metadata: Metadata; level: string; setLevel: (value: string) => void } & ExecutionProps) {
  const [draft, setDraft] = useState<Draft>(initialDraft ?? { agregado_id: metadata.id, nivel_id: level, variavel_ids: [], localidade_ids: [], periodo_ids: [], classificacoes: metadata.classificacoes.map(v => ({ classificacao_id: v.id, categoria_ids: [] })) })
  const [locationSearch, setLocationSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedLocations, setSelectedLocations] = useState<Item[]>([])
  const [submitted, setSubmitted] = useState<Draft | null>(initialDraft ?? null)
  const [copied, setCopied] = useState('')
  const active = useRef<AbortController | null>(null)
  const [executing, setExecuting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  useEffect(() => () => { active.current?.abort() }, [])
  async function search() {
    active.current?.abort()
    const controller = new AbortController()
    active.current = controller
    setExecuting(true); setExecutionError('')
    try {
      const response = await executeDraft(structuredClone(draft), controller.signal)
      if (!controller.signal.aborted && active.current === controller) onResult(response)
    } catch (error) {
      if (!controller.signal.aborted && active.current === controller) setExecutionError(error instanceof Error ? error.message : 'Falha ao buscar resultados.')
    } finally {
      if (active.current === controller) setExecuting(false)
    }
  }
  const periods = useQuery({ queryKey: ['periodos', metadata.id], queryFn: ({ signal }) => getPeriods(metadata.id, signal), staleTime: 60_000 })
  const locations = useQuery({ queryKey: ['localidades', metadata.id, level, locationSearch, page], queryFn: ({ signal }) => getLocations(metadata.id, { nivel: level, q: locationSearch, page: String(page) }, signal), enabled: !!level, staleTime: 60_000 })
  const validation = useQuery({ queryKey: ['validar', submitted], queryFn: ({ signal }) => validateDraft(submitted!, signal), enabled: !!submitted, retry: false, staleTime: Infinity, gcTime: 0, refetchOnWindowFocus: false })
  function update(next: Draft) {
    active.current?.abort(); active.current = null
    setExecuting(false); setExecutionError('')
    setSubmitted(null); setCopied('')
    next.classificacoes = next.classificacoes.map(chosen => {
      const classification = metadata.classificacoes.find(v => v.id === chosen.classificacao_id)
      if (!classification) return chosen
      const totalAllowed = classification.sumarizacao.status && !next.variavel_ids.some(id => classification.sumarizacao.excecao.includes(id))
      return { ...chosen, categoria_ids: chosen.categoria_ids.filter(id => id !== '0' || totalAllowed) }
    })
    onDraftChange(next)
    setDraft(next)
  }
  const ready = !!level && draft.variavel_ids.length > 0 && draft.localidade_ids.length > 0 && draft.periodo_ids.length > 0 && draft.classificacoes.every(v => v.categoria_ids.length > 0) && periods.isSuccess && locations.isSuccess
  return <section aria-label="Editor de consulta"><h2>Seleção da consulta</h2>
    <label>Nível da consulta<select aria-label="Nível publicado do agregado" value={level} onChange={e => { setLevel(e.target.value); setPage(1); setLocationSearch(''); setSelectedLocations([]); update({ ...draft, nivel_id: e.target.value, localidade_ids: [] }) }}><option value="">Selecione…</option>{Array.from(new Map(metadata.niveis.map(v => [v.id, v])).values()).map(v => <option key={v.id} value={v.id}>{v.id} · {v.nome ?? v.id}</option>)}</select></label>
    <Multi label="Variáveis da consulta" items={metadata.variaveis.map(v => ({ ...v, nome: `${v.nome} · ${v.unidade ?? 'Unidade não informada'}` }))} values={draft.variavel_ids} change={ids => update({ ...draft, variavel_ids: ids })} />
    <QueryFeedback query={periods} />
    {periods.isSuccess && <><Multi label="Períodos da consulta" items={periods.data.data.items.map(v => ({ id: v.id, nome: v.literals.join(' / ') }))} values={draft.periodo_ids} change={ids => update({ ...draft, periodo_ids: ids })} /><button disabled={!periods.data.data.items.length} onClick={() => update({ ...draft, periodo_ids: periods.data.data.items.map(v => v.id) })}>Selecionar todos os períodos publicados</button></>}
    <label>Buscar localidades por código ou nome<input value={locationSearch} onChange={e => { setLocationSearch(e.target.value); setPage(1) }} /></label>
    <QueryFeedback query={locations} />
    {!!level && locations.isSuccess && <><Multi label="Localidades da consulta" items={locations.data.data.items} values={draft.localidade_ids} change={ids => { setSelectedLocations(previous => [...previous.filter(v => ids.includes(v.id)), ...locations.data.data.items.filter(v => ids.includes(v.id) && !previous.some(p => p.id === v.id))]); update({ ...draft, localidade_ids: ids }) }} /><nav aria-label="Páginas de localidades"><button disabled={page === 1 || locations.isFetching} onClick={() => setPage(page - 1)}>Localidades anteriores</button><span>Página {page} · {locations.data.data.pagination.total_count} localidades</span><button disabled={!locations.data.data.pagination.has_next || locations.isFetching} onClick={() => setPage(page + 1)}>Próximas localidades</button></nav></>}
    <ul aria-label="Localidades selecionadas">{draft.localidade_ids.map(id => selectedLocations.find(v => v.id === id) ?? locations.data?.data.items.find(v => v.id === id) ?? { id, nome: 'Código selecionado' }).map(v => <li key={v.id}>{v.id} · {v.nome} <button onClick={() => { setSelectedLocations(previous => previous.filter(p => p.id !== v.id)); update({ ...draft, localidade_ids: draft.localidade_ids.filter(id => id !== v.id) }) }}>Remover {v.id}</button></li>)}</ul>
    {metadata.classificacoes.map(c => {
      const allowed = c.sumarizacao.status && !draft.variavel_ids.some(id => c.sumarizacao.excecao.includes(id))
      const items = c.categorias.filter(v => v.id !== '0').map(v => ({ ...v, nome: `${v.nome} · hierarquia ${v.nivel ?? 'não informada'}${v.unidade ? ` · ${v.unidade}` : ''}` }))
      if (allowed) items.unshift({ id: '0', nome: 'Total especial da API', unidade: null, nivel: null })
      return <div key={c.id}><Multi label={`Classificação ${c.id} · ${c.nome}`} items={items} values={draft.classificacoes.find(v => v.classificacao_id === c.id)?.categoria_ids ?? []} change={ids => update({ ...draft, classificacoes: draft.classificacoes.map(v => v.classificacao_id === c.id ? { ...v, categoria_ids: ids } : v) })} />{!allowed && <p>Total especial indisponível para as variáveis selecionadas ou para esta classificação.</p>}</div>
    })}
    <button disabled={!ready || executing || (!!initialDraft && !!submitted && !validation.isSuccess)} onClick={() => void search()}>Buscar</button>
    {executing && <p role="status">Buscando resultado…</p>}
    {executionError && <p role="alert">{executionError} Ajuste o recorte ou use Buscar para tentar novamente.</p>}
    <button disabled={!ready || validation.isFetching} onClick={() => { setSubmitted(structuredClone(draft)); if (submitted) void validation.refetch() }}>Validar seleção e gerar URL</button>
    {submitted && <QueryFeedback query={validation} />}
    {submitted && validation.isSuccess && <div role="region" aria-label="Consulta validada"><p>Consulta validada · {validation.data.data.estimated_observations} observações estimadas</p><label>URL oficial<textarea aria-label="URL oficial" readOnly value={validation.data.data.source_url} /></label><button onClick={() => { void navigator.clipboard.writeText(validation.data.data.source_url).then(() => setCopied('URL copiada.')).catch(() => setCopied('Selecione e copie a URL no campo acima.')) }}>Copiar URL oficial</button><p role="status">{copied}</p><QueryShare draft={validation.data.data.consulta_resolvida} /></div>}
  </section>
}
