import { useState, type FormEvent } from 'react'
import { ApiError, login } from '../api/client'
import { getAuthenticatedContext } from '../api/organizationContext'
import { GoogleSignIn } from '../components/GoogleSignIn'

export function LoginPage({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try { await login(email, password); await getAuthenticatedContext(); onAuthenticated() }
    catch (cause) { setError(cause instanceof ApiError && cause.status === 401 ? 'Incorrect email or password.' : 'Unable to sign in. Please try again.') }
    finally { setSubmitting(false) }
  }

  return <main className="login-page"><form className="login-card" onSubmit={submit}>
    <p className="section-kicker">BWIP / INTERNAL PLATFORM</p><h1>Sign in</h1>
    <p className="login-help">Use your BWIP account to open the evidence-led workspace.</p>
    <GoogleSignIn password={password} onAuthenticated={onAuthenticated} />
    <label>Email<input aria-label="Email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
    <label>Password<input aria-label="Password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
    {error && <p className="login-error" role="alert">{error}</p>}
    <button className="login-submit" type="submit" disabled={submitting}>{submitting ? 'Signing in…' : 'Sign in'}</button>
  </form></main>
}
