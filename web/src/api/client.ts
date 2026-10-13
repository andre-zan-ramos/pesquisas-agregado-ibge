export class ApiError extends Error {
  constructor(message: string, readonly code: string, readonly status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function getApi<T>(path: string, signal?: AbortSignal, params?: Record<string, string>): Promise<T> {
  if (!/^\/[a-z0-9/-]+\/$/.test(path)) throw new ApiError('Caminho de API inválido.', 'invalid_path')
  const timeout = AbortSignal.timeout(60_000)
  const requestSignal = signal ? AbortSignal.any([signal, timeout]) : timeout
  let response: Response
  try {
    const query = new URLSearchParams(params)
    response = await fetch(`/api/v1/agregados-ibge${path}${query.size ? `?${query}` : ''}`, { signal: requestSignal, headers: { Accept: 'application/json' } })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new ApiError(timeout.aborted ? 'O servidor excedeu o tempo de resposta.' : 'Não foi possível conectar ao servidor.', timeout.aborted ? 'timeout' : 'network_error')
  }
  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw new ApiError('O servidor retornou uma resposta inválida.', 'invalid_response', response.status)
  }
  if (!response.ok) {
    const error = (body as { error?: { message?: unknown; code?: unknown } } | null)?.error
    throw new ApiError(typeof error?.message === 'string' ? error.message : 'Não foi possível atender à solicitação.', typeof error?.code === 'string' ? error.code : 'http_error', response.status)
  }
  return body as T
}
