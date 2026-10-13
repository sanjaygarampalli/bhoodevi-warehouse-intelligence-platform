export type ApiErrorKind = 'authentication' | 'forbidden' | 'not-found' | 'validation' | 'network' | 'server'

export class ApiError extends Error {
  constructor(public readonly status: number | undefined, message: string) {
    super(message)
    this.name = 'ApiError'
  }

  get kind(): ApiErrorKind {
    if (this.status === 401) return 'authentication'
    if (this.status === 403) return 'forbidden'
    if (this.status === 404) return 'not-found'
    if (this.status === 422) return 'validation'
    if (this.status === undefined) return 'network'
    return 'server'
  }
}

// The FastAPI development server is documented to run on port 8000. Keep the
// backend origin independent from the browser origin so LAN/mobile clients do
// not accidentally send API requests to the Vite server.
const configuredApiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim()
const API_BASE_URL = (configuredApiBaseUrl || 'http://localhost:8000').replace(/\/+$/, '')

const TOKEN_KEY = 'bwip_access_token'

export function getAccessToken(): string | null {
  // Retire persistent credentials without copying them into the new store.
  // Existing installations must sign in again; server expiry/revocation still applies.
  window.localStorage.removeItem(TOKEN_KEY)
  return window.sessionStorage.getItem(TOKEN_KEY)
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken()
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, credentials: 'omit' })
  } catch {
    throw new ApiError(undefined, 'The BWIP backend could not be reached.')
  }

  if (!response.ok) {
    // A late response from an old session must not erase a newer sign-in.
    if (response.status === 401 && token === getAccessToken()) { clearAccessToken(); window.dispatchEvent(new Event('bwip-session-expired')) }
    let detail = 'The BWIP backend returned an error.'
    try {
      const body = await response.json() as { detail?: string | Array<{ msg?: string }> }
      if (typeof body.detail === 'string' && body.detail) detail = body.detail
      else if (Array.isArray(body.detail)) detail = 'The submitted data did not pass validation.'
    } catch { /* Keep the safe generic message. */ }
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<T>
}

export function clearAccessToken() {
  window.sessionStorage.removeItem(TOKEN_KEY)
  window.localStorage.removeItem(TOKEN_KEY)
}

export async function logoutAccount(): Promise<void> {
  await apiRequest<{ detail: string }>('/auth/logout', { method: 'POST' })
  clearAccessToken()
}

export async function googleRequest<T>(path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/auth/google${path}`, {
      method: body === undefined ? 'GET' : 'POST', credentials: 'omit',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    })
  } catch { throw new ApiError(undefined, 'The BWIP backend could not be reached.') }
  if (!response.ok) {
    let detail = 'Google sign-in could not be completed. Try again.'
    try { const result = await response.json(); if (typeof result.detail === 'string') detail = result.detail } catch { /* safe message */ }
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<T>
}

export async function loginWithGoogle(credential: string, nonce: string, linkPassword?: string) {
  const result = await googleRequest<{ access_token: string; token_type: string }>('', {
    credential, nonce, ...(linkPassword ? { link_password: linkPassword } : {}),
  })
  window.localStorage.removeItem(TOKEN_KEY)
  window.sessionStorage.setItem(TOKEN_KEY, result.access_token)
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password })
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
    credentials: 'omit',
  })
  if (!response.ok) {
    let detail = 'Sign-in failed.'
    try { detail = ((await response.json()) as { detail?: string }).detail || detail } catch { /* safe generic message */ }
    throw new ApiError(response.status, detail)
  }
  const result = await response.json() as { access_token: string; token_type: string }
  window.localStorage.removeItem(TOKEN_KEY)
  window.sessionStorage.setItem(TOKEN_KEY, result.access_token)
  return result
}
