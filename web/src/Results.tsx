import { useState } from 'react'
import type { Envelope } from './api/catalogo'
import type { Analysis, Category, Result } from './api/consultas'

const categories = (items: Category[]) => items.map(c => `${c.classificacao_id} · ${c.classificacao_nome}: ${c.categoria_id} · ${c.categoria_nome}`).join(' / ')
const display = (value: number | null) => value === null ? 'Indisponível' : String(value)

function Chart({ analysis, result }: { analysis: Analysis; result: Result }) {
  if (!analysis.grafico_linhas) return <p>Gráfico de linhas suspenso. {analysis.avisos[0]}</p>
  const points = analysis.pontos
  const numbers = points.flatMap(p => p.valor === null ? [] : [p.valor])
  if (!numbers.length) return <p>Sem observações numéricas para o gráfico.</p>
  const low = Math.min(...numbers), high = Math.max(...numbers)
  const magnitude = Math.max(Math.abs(low), Math.abs(high), 1)
  const normalizedLow = low / magnitude, normalizedHigh = high / magnitude
  const x = (i: number) => 65 + i * 570 / Math.max(points.length - 1, 1)
  const y = (v: number) => 190 - (v / magnitude - normalizedLow) / (normalizedHigh - normalizedLow || 1) * 150
  // Each null ends the path, including published markers and unreturned periods.
  let drawing = false
  const path = points.map((p, i) => {
    if (p.valor === null) { drawing = false; return '' }
    const command = drawing ? 'L' : 'M'; drawing = true
    return `${command}${x(i)},${y(p.valor)}`
  }).join(' ')
  return <figure><svg viewBox="0 0 700 255" role="img" aria-label={`Série ${analysis.variavel_id}, ${analysis.localidade_id}, ${analysis.unidade}. Tabela longa disponível abaixo.`}>
    <line x1="65" y1="205" x2="635" y2="205" stroke="currentColor" />
    <text x="0" y="30">{high}</text><text x="0" y="195">{low}</text>
    <path data-testid="series-path" d={path} fill="none" stroke="#13796b" strokeWidth="2" />
    {points.map((p, i) => p.valor === null ? null : <circle key={p.periodo_id} cx={x(i)} cy={y(p.valor)} r="4" fill="#13796b"><title>{p.periodo_id}: {p.valor}</title></circle>)}
    {points.filter((_, i) => points.length <= 8 || i === 0 || i === points.length - 1).map(p => <text key={p.periodo_id} x={x(points.indexOf(p))} y="232" textAnchor="middle">{p.periodo_id}</text>)}
  </svg><figcaption>{analysis.unidade} · {points.map(p => `${p.periodo_id} (${result.metadados.periodos.find(v => v.id === p.periodo_id)?.literals.join(' / ') ?? p.periodo_id})${p.lacuna ? ': lacuna, não retornado' : p.valor === null ? ': sem número' : ''}`).join(' · ')}</figcaption></figure>
}

export default function Results({ response, pending }: { response: Envelope<Result>; pending: boolean }) {
  const result = response.data
  const [page, setPage] = useState(1)
  const [variable, setVariable] = useState(result.consulta_aplicada.variavel_ids[0])
  const [analysisIndex, setAnalysisIndex] = useState(0)
  const rows = result.observacoes.filter(r => r.variavel_id === variable)
  const analyses = result.analises.filter(a => a.variavel_id === variable)
  const analysis = analyses[analysisIndex]
  return <section aria-label="Resultado aplicado"><h2>Resultado · {result.consulta_aplicada.agregado_id}</h2>
    {pending && <p role="status">Alterações pendentes. O último resultado aplicado está preservado; use Buscar para atualizar.</p>}
    <details><summary>Consulta aplicada e proveniência</summary><pre>{JSON.stringify(result.consulta_aplicada, null, 2)}</pre><p>Normalizador {result.normalizer_version} · resposta completa</p>{response.sources.map((s, i) => <p key={i}><a href={s.source_url}>{s.source_url}</a><br />Obtido em {s.fetched_at} · expira em {s.expires_at} · {s.cache_hit ? 'cache' : 'fonte'}</p>)}</details>
    {result.warnings.length > 0 && <details><summary>Avisos ({result.warnings.length})</summary>{result.warnings.map((w, i) => <p key={i}>{w.code}: {w.message}</p>)}</details>}
    {result.observacoes.length === 0 ? <p role="status">Nenhuma observação retornada para a consulta aplicada.</p> : <>
      <label>Variável do resultado<select value={variable} onChange={e => { setVariable(e.target.value); setPage(1); setAnalysisIndex(0) }}>{result.consulta_aplicada.variavel_ids.map(id => <option key={id} value={id}>{id} · {result.metadados.variaveis.find(v => v.id === id)?.nome}</option>)}</select></label>
      <label>Combinação para gráfico e estatísticas<select value={analysisIndex} onChange={e => setAnalysisIndex(Number(e.target.value))}>{analyses.map((a, i) => <option key={i} value={i}>{a.nivel_id}/{a.localidade_id} · {a.localidade_nome} · {categories(a.classificacoes)}</option>)}</select></label>
      {analysis && <div aria-label="Análise da combinação"><h3>{analysis.nivel_id}/{analysis.localidade_id} · {analysis.localidade_nome}</h3><p>{categories(analysis.classificacoes)} · Unidade: {analysis.unidade ?? 'não utilizável'}</p><Chart analysis={analysis} result={result} />
        <p>{analysis.n} observações numéricas · {analysis.sem_numero} sem número (lacunas não contam).</p>
        {analysis.pontos.some(p => p.lacuna) && <p>Lacunas (não retornadas): {analysis.pontos.filter(p => p.lacuna).map(p => p.periodo_id).join(', ')}. Nenhuma observação foi criada.</p>}
        {analysis.suspensa ? <p>Estatísticas suspensas: unidade conflitante ou não confirmada.</p> : <dl className="statistics"><dt>Média</dt><dd>{display(analysis.media)}</dd><dt>Desvio amostral</dt><dd>{display(analysis.desvio)}</dd><dt>CV (%)</dt><dd>{display(analysis.cv)}</dd><dt>Mínimo</dt><dd>{display(analysis.minimo)} · {analysis.periodos_min.join(', ')}</dd><dt>Máximo</dt><dd>{display(analysis.maximo)} · {analysis.periodos_max.join(', ')}</dd></dl>}
        {analysis.avisos.map((a, i) => <p key={i}>{a}</p>)}
      </div>}
      <h3>Tabela longa · {rows.length} ocorrências</h3><p>Marcadores X/x, .., ... e - permanecem literais; não são convertidos em zero.</p>
      <div className="table-scroll" role="region" aria-label="Tabela longa rolável" tabIndex={0}><table><caption>Observações da variável {variable}, com todas as categorias e ocorrências</caption><thead><tr>{['Variável', 'Localidade', 'Período', 'Categorias', 'Valor original', 'Número', 'Status', 'Unidade da resposta', 'Unidades das categorias', 'Unidade analítica', 'Origem (variável/resultado/série)'].map(h => <th key={h} scope="col">{h}</th>)}</tr></thead><tbody>{rows.slice((page - 1) * 50, page * 50).map((r, i) => <tr key={i}><td>{r.variavel_id} · {r.variavel_nome}</td><td>{r.nivel_id}/{r.localidade_id} · {r.localidade_nome}</td><td>{r.periodo_id} · {result.metadados.periodos.find(p => p.id === r.periodo_id)?.literals.join(' / ')}</td><td>{categories(r.classificacoes)}</td><td className="literal">{r.valor_original === null ? 'null (JSON)' : r.valor_original === '' ? '"" (vazio)' : String(r.valor_original)}</td><td>{display(r.valor_numerico)}</td><td>{r.valor_status}</td><td>{r.unidade_original ?? 'não informada'}</td><td>{r.classificacoes.map(c => `${c.classificacao_id}/${c.categoria_id}: ${c.categoria_unidade ?? 'não informada'}`).join(' / ')}</td><td>{r.unidade ?? 'suspensa'} · {r.unidade_status}</td><td>{r.origem_indice.variavel}/{r.origem_indice.resultado}/{r.origem_indice.serie}</td></tr>)}</tbody></table></div>
      <nav aria-label="Páginas do resultado"><button disabled={page === 1} onClick={() => setPage(page - 1)}>Observações anteriores</button><span>Página {page}</span><button disabled={page * 50 >= rows.length} onClick={() => setPage(page + 1)}>Próximas observações</button></nav>
    </>}
  </section>
}
