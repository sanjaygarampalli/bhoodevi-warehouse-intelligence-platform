import { afterEach, expect, it, vi } from 'vitest'
import { apiRequest, getAccessToken, login, logoutAccount } from './client'

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); sessionStorage.clear() })

it('retires legacy tokens without migration and sends only tab bearer credentials', async () => {
  localStorage.setItem('bwip_access_token', 'legacy')
  expect(getAccessToken()).toBeNull()
  expect(localStorage.getItem('bwip_access_token')).toBeNull()
  const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ access_token: 'tab-token', token_type: 'bearer' })))
  vi.stubGlobal('fetch', fetchMock)
  await login('synthetic@example.com', 'synthetic-password')
  expect(sessionStorage.getItem('bwip_access_token')).toBe('tab-token')
  await apiRequest('/auth/me')
  const options = fetchMock.mock.calls[1][1] as RequestInit
  expect(new Headers(options.headers).get('Authorization')).toBe('Bearer tab-token')
  expect(options.credentials).toBe('omit')
  expect(fetchMock.mock.calls[0][1].credentials).toBe('omit')
})

it('keeps credentials on failed logout and clears them after confirmed revocation', async () => {
  sessionStorage.setItem('bwip_access_token', 'tab-token')
  const fetchMock = vi.fn().mockRejectedValueOnce(new Error('network')).mockResolvedValueOnce(new Response('{"detail":"revoked"}'))
  vi.stubGlobal('fetch', fetchMock)
  await expect(logoutAccount()).rejects.toThrow('could not be reached')
  expect(getAccessToken()).toBe('tab-token')
  await logoutAccount()
  expect(getAccessToken()).toBeNull()
})

it('a delayed unauthorized response cannot erase a newer login', async () => {
  sessionStorage.setItem('bwip_access_token', 'old-token')
  let finish!: (response: Response) => void
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve })))
  const pending = apiRequest('/auth/me')
  sessionStorage.setItem('bwip_access_token', 'new-token')
  finish(new Response('{"detail":"revoked"}', { status: 401 }))
  await expect(pending).rejects.toThrow('revoked')
  expect(getAccessToken()).toBe('new-token')
})
