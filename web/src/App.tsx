import { useQuery } from '@tanstack/react-query'
import { getApi } from './api/client'

export default function App() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async ({ signal }) => {
      const data = await getApi<{ status?: string }>('/health/', signal)
      if (data.status !== 'ok') throw new Error('O servidor retornou um estado inesperado.')
      return data
    },
    staleTime: 30_000,
  })
  return (
    <main>
      <header><a className="brand" href="/">Pesquisas IBGE</a><span className="tag">Agregados</span></header>
      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">EXPLORADOR DE DADOS</p>
        <h1 id="page-title">Um caminho mais simples<br />para explorar as pesquisas.</h1>
        <p>Pesquisas, territórios e indicadores em um só lugar.</p>
      </section>
      <section className="welcome" aria-labelledby="welcome-title">
        <span className="number" aria-hidden="true">01</span>
        <div><h2 id="welcome-title">O explorador está em preparação</h2><p>A seleção de pesquisas e agregados será disponibilizada na próxima etapa.</p></div>
      </section>
      <div className="status" role="status" aria-live="polite">
        <span className={`dot ${health.isError ? 'error' : health.isSuccess ? 'ready' : ''}`} aria-hidden="true" />
        <span>{health.isPending ? 'Conectando ao servidor…' : health.isError ? health.error.message : 'Servidor disponível'}</span>
        {health.isError && <button disabled={health.isFetching} onClick={() => void health.refetch()}>{health.isFetching ? 'Conectando…' : 'Tentar novamente'}</button>}
      </div>
      <footer>Fonte de referência: Instituto Brasileiro de Geografia e Estatística.</footer>
    </main>
  )
}
