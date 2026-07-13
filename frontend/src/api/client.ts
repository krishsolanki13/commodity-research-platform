const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export interface ApiErrorPayload {
  code: string
  message: string
  detail?: string
  fieldErrors?: Record<string, string>
  status: number
}

export class ApiClientError extends Error {
  readonly apiError: ApiErrorPayload

  constructor(payload: ApiErrorPayload) {
    super(payload.message)
    this.name = 'ApiClientError'
    this.apiError = payload
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`

  let response: Response
  try {
    response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })
  } catch {
    throw new ApiClientError({
      code: 'NETWORK_ERROR',
      message: 'Cannot reach the API server. Is `make dev` running?',
      status: 0,
    })
  }

  if (!response.ok) {
    let envelope: {
      error?: {
        code?: string
        message?: string
        detail?: string
        field_errors?: Record<string, string>
      }
    }
    try {
      envelope = (await response.json()) as typeof envelope
    } catch {
      envelope = {}
    }

    throw new ApiClientError({
      code: envelope.error?.code ?? 'UNKNOWN',
      message: envelope.error?.message ?? `HTTP ${response.status}`,
      detail: envelope.error?.detail,
      fieldErrors: envelope.error?.field_errors,
      status: response.status,
    })
  }

  return response.json() as Promise<T>
}

export const client = {
  get: <T>(path: string): Promise<T> => request<T>(path),
  post: <T>(path: string, body: unknown): Promise<T> =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  delete: <T>(path: string): Promise<T> => request<T>(path, { method: 'DELETE' }),
}
