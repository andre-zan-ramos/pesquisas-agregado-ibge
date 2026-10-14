import { useState } from 'react'
import Editor from './Editor'
import { useQuery } from '@tanstack/react-query'
import { getDomains, getMetadata, getResearches, type Item, type Metadata, type Source } from './api/catalogo'

function Picker({ label, items, value, onChange, disabled = false }: { label: string; items: Item[]; value: string; onChange: (value: string) => void; disabled?: boolean }) {
  const [search, setSearch] = useState('')
  const filtered = items.filter(item => `${item.id} ${item.nome}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
  const options = items.filter(item => item.id === value || filtered.includes(item))
  return <fieldset disabled={disabled} className="picker"><legend>{label}</legend>
    <input aria-label={`Buscar ${label.toLocaleLowerCase()} por código ou nome`} placeholder="Código ou nome" value={search} onChange={event => setSearch(event.target.value)} />
    <select aria-label={label} value={value} onChange={event => onChange(event.target.value)}><option value="">Selecione…</option>{options.map(item => <option key={item.id} value={item.id}>{item.id} · {item.nome}</option>)}</select>
    {search && filtered.length === 0 && <span role="status">Nenhum item encontrado.</span>}
  </fieldset>
}

function Feedback({ loading, error, retry }: { loading: boolean; error: Error | null; retry: () => void }) {
  if (error) return <div role="alert" className="status">{error.message} <button onClick={retry} disabled={loading}>Tentar novamente</button></div>
  return loading ? <p role="status">Carregando…</p> : null
}

function Provenance({ sources }: { sources: Source[] }) {
  return <details><summary>Origem e cache</summary>{sources.map(source => <p key={source.source_url}><a href={source.source_url}>{source.source_url}</a><br />Obtido em {source.fetched_at} · válido até {source.expires_at} · {source.cache_hit ? 'cache' : 'obtido da fonte'}</p>)}</details>
}

function MetadataView({ data, sources }: { data: Metadata; sources: Source[] }) {
  const [level, setLevel] = useState(data.niveis.some(item => item.id === 'N6') ? 'N6' : '')
  return <section className="metadata" aria-labelledby="metadata-title"><h2 id="metadata-title">{data.id} · {data.nome}</h2>
    <p>{data.pesquisa} · {data.assunto}</p><p>{data.periodicidade.frequencia} · {data.periodicidade.inicio} a {data.periodicidade.fim}</p><p>Referência SIDRA: {data.sidra_url}</p>
    <Editor key={JSON.stringify(data)} metadata={data} level={data.niveis.some(item => item.id === level) ? level : ''} setLevel={setLevel} />
    {data.niveis.length === 0 && <p role="status">Nenhum nível territorial publicado.</p>}
    <details open><summary>Todos os grupos territoriais</summary>{Array.from(new Set(data.niveis.map(item => item.grupo))).map(group => <div key={group}><h3>{group}</h3>{!['Administrativo', 'Especial', 'IBGE'].includes(group) && <p>Grupo adicional publicado pela fonte.</p>}<ul>{data.niveis.filter(item => item.grupo === group).map((item, index) => <li key={`${item.id}-${index}`}>{item.id} · {item.nome ?? 'Nome não publicado no acervo'}</li>)}</ul></div>)}</details>
    <details><summary>Variáveis e unidades ({data.variaveis.length})</summary>{data.variaveis.map((item, index) => <div key={`${item.id}-${index}`}><h3>{item.id} · {item.nome}</h3><p>Unidade: {item.unidade ?? 'Não informada'}<br />Sumarização: {item.sumarizacao.join(', ') || 'Nenhuma'}</p></div>)}</details>
    <details><summary>Classificações e categorias ({data.classificacoes.length})</summary>{data.classificacoes.map((item, index) => <div key={`${item.id}-${index}`}><h3>{item.id} · {item.nome}</h3><p>Total especial da API (0): {item.sumarizacao.status ? 'Permitido, sujeito às exceções' : 'Não permitido'}<br />Variáveis com exceção de total: {item.sumarizacao.excecao.join(', ') || 'Nenhuma'}</p><ul>{item.categorias.map((category, position) => <li key={`${category.id}-${position}`}>{category.id} · {category.nome} · Unidade: {category.unidade ?? 'Não informada'} · Hierarquia: {category.nivel ?? 'Não informada'}</li>)}</ul></div>)}</details>
    <details><summary>Períodos publicados ({data.periodos.length})</summary><ul>{data.periodos.map((item, index) => <li key={`${item.id}-${index}`}>{item.id} · {item.literals.join(' / ')} · Modificação: {item.modificacao ?? 'Não informada'} · Ordem na fonte: {item.ordem}</li>)}</ul></details>
    <Provenance sources={sources} />
  </section>
}

function Discovery({ domains }: { domains: Awaited<ReturnType<typeof getDomains>> }) {
  const [selection, setSelection] = useState({ assunto: '', nivel: domains.data.niveis.some(item => item.id === 'N6') ? 'N6' : '', periodo: '', q: '', page: 1, pesquisa: '', agregado: '' })
  const changeFilter = (key: 'assunto' | 'nivel' | 'periodo' | 'q', value: string) => setSelection(previous => ({ ...previous, [key]: value, page: 1, pesquisa: '', agregado: '' }))
  const params: Record<string, string> = { page: String(selection.page), page_size: '50' }
  for (const key of ['assunto', 'nivel', 'periodo', 'q'] as const) if (selection[key]) params[key] = selection[key]
  const catalog = useQuery({ queryKey: ['pesquisas', params], queryFn: ({ signal }) => getResearches(params, signal), staleTime: 60_000 })
  const researches = catalog.data?.data.items ?? []
  const research = researches.find(item => item.id === selection.pesquisa)
  const aggregate = research?.agregados.find(item => item.id === selection.agregado)
  const metadata = useQuery({ queryKey: ['metadados', aggregate?.id], queryFn: ({ signal }) => getMetadata(aggregate!.id, signal), enabled: !!aggregate, staleTime: 60_000 })
  return <><section aria-labelledby="discovery-title"><h2 id="discovery-title">Descubra uma pesquisa</h2>
    <div className="grid">{([['assunto', 'Assunto', domains.data.assuntos], ['nivel', 'Nível de descoberta', domains.data.niveis], ['periodo', 'Período de descoberta', domains.data.periodos]] as const).map(([key, label, items]) => <Picker key={key} label={label} items={items} value={selection[key]} onChange={value => changeFilter(key, value)} />)}</div>
    <label className="catalog-search">Buscar pesquisas e agregados por código ou nome<input value={selection.q} onChange={event => changeFilter('q', event.target.value)} placeholder="Código ou nome da pesquisa ou agregado" /></label>
    <Feedback loading={catalog.isFetching} error={catalog.error} retry={() => void catalog.refetch()} />
    {catalog.isSuccess && researches.length === 0 && <p role="status">Nenhuma pesquisa encontrada para os filtros.</p>}
    <div className="grid"><Picker label="Pesquisa" items={researches} value={research?.id ?? ''} disabled={!catalog.isSuccess || catalog.isFetching} onChange={value => setSelection(previous => ({ ...previous, pesquisa: value, agregado: '' }))} />
      <Picker key={research?.id ?? 'empty'} label="Agregado" items={research?.agregados ?? []} value={aggregate?.id ?? ''} disabled={!research || catalog.isFetching} onChange={value => setSelection(previous => ({ ...previous, agregado: value }))} /></div>
    {research && research.agregados.length === 0 && <p role="status">Nenhum agregado publicado nesta pesquisa.</p>}
    {catalog.data && <nav aria-label="Páginas de pesquisas"><button disabled={selection.page === 1 || catalog.isFetching} onClick={() => setSelection(previous => ({ ...previous, page: previous.page - 1, pesquisa: '', agregado: '' }))}>Anterior</button><span>Página {selection.page} · {catalog.data.data.pagination.total_count} pesquisas</span><button disabled={!catalog.data.data.pagination.has_next || catalog.isFetching} onClick={() => setSelection(previous => ({ ...previous, page: previous.page + 1, pesquisa: '', agregado: '' }))}>Próxima</button></nav>}
    </section>{aggregate && <Feedback loading={metadata.isFetching} error={metadata.error} retry={() => void metadata.refetch()} />}
    {aggregate && metadata.isSuccess && metadata.data.data.id === aggregate.id && <MetadataView key={aggregate.id} data={metadata.data.data} sources={metadata.data.sources} />}
    <Provenance sources={domains.sources} />
  </>
}

export default function App() {
  const domains = useQuery({ queryKey: ['dominios'], queryFn: ({ signal }) => getDomains(signal), staleTime: 60_000 })
  return <main><header><a className="brand" href="/">Pesquisas IBGE</a><span className="tag">Agregados</span></header>
    <section className="intro"><p className="eyebrow">EXPLORADOR DE DADOS</p><h1>Explore pesquisas<br />e seus agregados.</h1><p>Encontre um agregado e conheça suas dimensões publicadas.</p></section>
    <Feedback loading={domains.isFetching} error={domains.error} retry={() => void domains.refetch()} />{domains.isSuccess && <Discovery domains={domains.data} />}
    <footer>Fonte: Instituto Brasileiro de Geografia e Estatística.</footer></main>
}
