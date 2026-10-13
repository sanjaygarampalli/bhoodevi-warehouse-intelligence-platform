import { useEffect, useRef, useState } from 'react'
import { googleRequest, loginWithGoogle } from '../api/client'
import { getAuthenticatedContext } from '../api/organizationContext'

type GoogleIdentity = {
  initialize: (options: { client_id: string; nonce: string; auto_select: boolean; callback: (result: { credential: string }) => void }) => void
  renderButton: (element: HTMLElement, options: { type: string; theme: string; size: string }) => void
}
declare global { interface Window { google?: { accounts: { id: GoogleIdentity } } } }

let sdk: Promise<void> | undefined
function loadGoogle(): Promise<void> {
  if (window.google?.accounts.id) return Promise.resolve()
  if (!sdk) sdk = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    const timer = window.setTimeout(() => { script.remove(); reject(new Error('Google sign-in could not load. Check your connection and retry.')) }, 15000)
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => { window.clearTimeout(timer); resolve() }
    script.onerror = () => { window.clearTimeout(timer); script.remove(); reject(new Error('Google sign-in could not load. Check your connection and retry.')) }
    document.head.appendChild(script)
  }).catch(error => { sdk = undefined; throw error })
  return sdk
}

export function GoogleSignIn({ password, onAuthenticated }: { password: string; onAuthenticated: () => void }) {
  const button = useRef<HTMLDivElement>(null)
  const latest = useRef({ password, onAuthenticated })
  latest.current = { password, onAuthenticated }
  const busy = useRef(false)
  const [state, setState] = useState('Checking Google sign-in…')
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    let expiry: number | undefined
    setError(''); setState('Checking Google sign-in…')
    async function prepare() {
      const config = await googleRequest<{ client_id: string | null }>('/config')
      if (!active) return
      if (!config.client_id) { setState('Google sign-in is not configured yet. Use your BWIP account below.'); return }
      await loadGoogle()
      if (!active) return
      const challenge = await googleRequest<{ nonce: string; expires_in: number }>('/challenge', {})
      if (!active || !button.current) return
      const identity = window.google?.accounts.id
      if (!identity) throw new Error('Google sign-in could not load. Retry.')
      identity.initialize({ client_id: config.client_id, nonce: challenge.nonce, auto_select: false,
        callback: async ({ credential }) => {
          if (!active || busy.current) return
          busy.current = true; setState('Signing in with Google…'); setError('')
          if (button.current) button.current.replaceChildren()
          window.clearTimeout(expiry)
          try {
            await loginWithGoogle(credential, challenge.nonce, latest.current.password)
            await getAuthenticatedContext()
            if (active) latest.current.onAuthenticated()
          } catch (cause) {
            if (active) { setError(cause instanceof Error ? cause.message : 'Google sign-in failed.'); setState('') }
          } finally { busy.current = false }
        },
      })
      button.current.replaceChildren()
      identity.renderButton(button.current, { type: 'standard', theme: 'outline', size: 'large' })
      setState('First time connecting Google? Enter your existing BWIP password below, then choose Google. No new account or organization access is created.')
      expiry = window.setTimeout(() => {
        if (active && !busy.current) { button.current?.replaceChildren(); setState(''); setError('Google sign-in expired. Retry to get a fresh sign-in button.') }
      }, challenge.expires_in * 1000)
    }
    prepare().catch(cause => { if (active) { setError(cause instanceof Error ? cause.message : 'Google sign-in is unavailable.'); setState('') } })
    return () => { active = false; window.clearTimeout(expiry); button.current?.replaceChildren() }
  }, [attempt])
  return <section aria-label="Google sign-in">
    <div ref={button} />
    {state && <p className="login-help" role="status">{state}</p>}
    {error && <><p className="login-error" role="alert">{error}</p><button type="button" onClick={() => setAttempt(value => value + 1)}>Retry Google sign-in</button></>}
  </section>
}
