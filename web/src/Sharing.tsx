import { useRef, useState } from 'react'
import type { Draft } from './api/consultas'
import { download, MAX_QUERY_BYTES, parseQuery, queryJSON, queryLink } from './query-transfer'

export function QueryShare({ draft }: { draft: Draft }) {
  const [message, setMessage] = useState('')
  const link = queryLink(draft)
  return <div aria-label="Compartilhar consulta">
    {link ? <><label>URL da aplicação<textarea readOnly value={link} /></label><button onClick={() => void navigator.clipboard.writeText(link).then(() => setMessage('Link copiado.')).catch(() => setMessage('Selecione e copie o link no campo.'))}>Copiar link da aplicação</button></> : <p role="status">A URL excede 2.000 caracteres. Exporte o JSON de consulta e importe na aplicação.</p>}
    <button onClick={() => download('consulta-ibge.json', queryJSON(draft), 'application/json;charset=utf-8')}>Exportar JSON de consulta</button><p role="status">{message}</p>
  </div>
}

export function QueryImport({ restore }: { restore: (draft: Draft) => void }) {
  const [error, setError] = useState('')
  const request = useRef(0)
  return <label>Importar JSON de consulta<input type="file" accept=".json,application/json" onChange={async e => {
    const current = ++request.current
    const file = e.target.files?.[0]; e.target.value = ''
    if (!file) return
    try {
      if (file.size > MAX_QUERY_BYTES) throw new Error('JSON de consulta excede 64 KiB.')
      const draft = parseQuery(await file.text())
      if (current !== request.current) return
      setError(''); restore(draft)
    } catch (err) { if (current === request.current) setError(err instanceof Error ? err.message : 'JSON inválido.') }
  }} />{error && <span role="alert">{error}</span>}</label>
}
