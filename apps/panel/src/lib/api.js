export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function apiUrl(path) {
  return import.meta.env.BASE_URL + path.replace(/^\/+/, '')
}

export async function request(path, { method = 'GET', body, csrf, signal } = {}) {
  const headers = { Accept: 'application/json' }
  const mutation = !['GET', 'HEAD'].includes(method.toUpperCase())
  if (mutation || body !== undefined) headers['Content-Type'] = 'application/json'
  if (csrf) headers['X-Archive-CSRF'] = csrf

  let response
  try {
    response = await fetch(apiUrl(path), {
      method,
      headers,
      credentials: 'same-origin',
      cache: 'no-store',
      body: body === undefined ? (mutation ? '{}' : undefined) : JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new ApiError('Não foi possível acessar o servidor. Tente novamente.', 0)
  }

  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : data?.message
    const messages = {
      csrf_invalid: 'A sessão mudou. Atualize a página para continuar.',
      invalid_csrf: 'A sessão mudou. Atualize a página para continuar.',
      invalid_credentials: 'Usuário ou senha incorretos.',
      evolution_unreachable: 'Não foi possível acessar a conexão do WhatsApp. Tente novamente.',
      evolution_not_configured: 'O servidor ainda precisa configurar a conexão do WhatsApp.',
      storage_full: 'A gravação está pausada por falta de espaço no servidor.',
      insufficient_storage: 'Não há espaço suficiente no servidor para continuar.',
      sync_already_running: 'Uma importação já está em andamento.',
    }
    const safeDetail = typeof detail === 'string' && !/^[a-z][a-z0-9_]+$/.test(detail) ? detail : null
    throw new ApiError(messages[detail] || safeDetail || 'Não foi possível concluir esta ação. Tente novamente.', response.status)
  }
  return data
}

export function queryString(values) {
  const query = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') query.set(key, value)
  })
  return query.toString()
}
