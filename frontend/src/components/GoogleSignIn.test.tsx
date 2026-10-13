import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { GoogleSignIn } from './GoogleSignIn'
import { googleRequest, loginWithGoogle } from '../api/client'
import { getAuthenticatedContext } from '../api/organizationContext'

vi.mock('../api/client', () => ({ googleRequest: vi.fn(), loginWithGoogle: vi.fn() }))
vi.mock('../api/organizationContext', () => ({ getAuthenticatedContext: vi.fn() }))
beforeEach(() => { vi.resetAllMocks(); delete window.google })
afterEach(cleanup)

it('does not load Google or ask for credentials when the integration is disabled', async () => {
  vi.mocked(googleRequest).mockResolvedValue({ client_id: null })
  render(<GoogleSignIn password="" onAuthenticated={vi.fn()} />)
  await screen.findByText(/Google sign-in is not configured yet/)
  expect(document.querySelector('script[src="https://accounts.google.com/gsi/client"]')).toBeNull()
  expect(loginWithGoogle).not.toHaveBeenCalled()
})

it('uses the challenge nonce and current linking password and ignores duplicate callbacks', async () => {
  let callback!: (result: { credential: string }) => void
  window.google = { accounts: { id: { initialize: vi.fn(options => { callback = options.callback }), renderButton: vi.fn() } } }
  vi.mocked(googleRequest).mockResolvedValueOnce({ client_id: 'synthetic' }).mockResolvedValueOnce({ nonce: 'synthetic-nonce', expires_in: 300 })
  let finish!: () => void
  vi.mocked(loginWithGoogle).mockImplementation(() => new Promise(resolve => { finish = resolve }))
  const done = vi.fn()
  const { rerender } = render(<GoogleSignIn password="" onAuthenticated={done} />)
  await waitFor(() => expect(window.google?.accounts.id.renderButton).toHaveBeenCalled())
  rerender(<GoogleSignIn password="existing-password" onAuthenticated={done} />)
  await act(async () => { callback({ credential: 'synthetic-token' }); callback({ credential: 'synthetic-token' }) })
  expect(loginWithGoogle).toHaveBeenCalledExactlyOnceWith('synthetic-token', 'synthetic-nonce', 'existing-password')
  await act(async () => { finish() })
  expect(getAuthenticatedContext).toHaveBeenCalledOnce()
  expect(done).toHaveBeenCalledOnce()
})

it('exposes errors and retries with a fresh challenge', async () => {
  let callback!: (result: { credential: string }) => void
  window.google = { accounts: { id: { initialize: vi.fn(options => { callback = options.callback }), renderButton: vi.fn() } } }
  vi.mocked(googleRequest).mockImplementation(async path => path === '/config' ? { client_id: 'synthetic' } : { nonce: 'new-nonce', expires_in: 300 })
  vi.mocked(loginWithGoogle).mockRejectedValue(new Error('Enter your BWIP password'))
  const done = vi.fn()
  render(<GoogleSignIn password="" onAuthenticated={done} />)
  await waitFor(() => expect(window.google?.accounts.id.renderButton).toHaveBeenCalled())
  await act(async () => { callback({ credential: 'synthetic' }) })
  await screen.findByRole('alert')
  expect(done).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Retry Google sign-in' }))
  await waitFor(() => expect(window.google?.accounts.id.renderButton).toHaveBeenCalledTimes(2))
})
