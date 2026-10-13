import { useEffect, useRef, useState } from 'react'
import { apiRequest, ApiError } from '../api/client'
import { getAuthenticatedContext } from '../api/organizationContext'
import type { MarketSignal, RequirementCandidate } from '../api/marketIntelligence'

export function MarketReviewControls({ signal, candidate, onSaved }: { signal: MarketSignal; candidate: RequirementCandidate | null; onSaved: () => void }) {
  const [canWrite, setCanWrite] = useState(false)
  const [notes, setNotes] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const pending = useRef(false)
  useEffect(() => {
    let active = true
    getAuthenticatedContext().then((context) => { if (active) setCanWrite(context.user.role === 'admin' || context.organizations.some((org) => org.organization_id === signal.organization_id && ['OWNER', 'ADMIN', 'MANAGER', 'MEMBER'].includes(org.role))) })
      .catch(() => { if (active) setMessage('Review permissions could not be loaded.') })
    return () => { active = false }
  }, [signal.organization_id])
  async function submit(path: string, payload: object, confirmation?: string) {
    if (pending.current || (confirmation && !window.confirm(confirmation))) return
    pending.current = true; setBusy(true); setMessage('')
    try {
      await apiRequest(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      onSaved()
    } catch (error: unknown) { setMessage(error instanceof ApiError ? error.message : 'Review could not be saved.') }
    finally { pending.current = false; setBusy(false) }
  }
  const signalPath = `/market-signals/${signal.id}/transition`
  const candidatePath = `/requirement-candidates/${candidate?.id}/transition`
  return <section className="panel"><h3>Human review</h3>
    {canWrite && <><label>Signal review notes<textarea value={notes} maxLength={5000} onChange={(event) => setNotes(event.target.value)} /></label><div className="conversion-form">
      {signal.status === 'DETECTED' && <button disabled={busy} onClick={() => void submit(signalPath, { target_status: 'UNDER_REVIEW', review_notes: notes })}>Begin signal review</button>}
      {signal.status === 'UNDER_REVIEW' && <><button disabled={busy} onClick={() => void submit(signalPath, { target_status: 'VERIFIED', review_notes: notes }, 'Verify this signal after checking its original evidence?')}>Verify signal</button><button disabled={busy} onClick={() => void submit(signalPath, { target_status: 'REJECTED', review_notes: notes })}>Reject signal</button></>}
      {signal.status === 'VERIFIED' && !candidate && <button disabled={busy} onClick={() => void submit(`/market-signals/${signal.id}/requirement-candidate`, {}, 'Create a requirement candidate for human qualification? This does not create a Lead or Deal.')}>Create requirement candidate</button>}
      {candidate?.status === 'CANDIDATE' && <button disabled={busy} onClick={() => void submit(candidatePath, { target_status: 'UNDER_REVIEW' })}>Begin candidate review</button>}
      {candidate?.status === 'UNDER_REVIEW' && <><button disabled={busy} onClick={() => void submit(candidatePath, { target_status: 'ACCEPTED' }, 'Accept this requirement candidate after reviewing the source evidence? Commercial conversion remains a separate action.')}>Accept candidate</button><button disabled={busy} onClick={() => void submit(candidatePath, { target_status: 'REJECTED' })}>Reject candidate</button></>}
    </div></>}
    <p className="search-note">Verification, candidate acceptance and commercial conversion remain separate human decisions. The server validates each transition.</p>
    {message && <p role="status">{message}</p>}
  </section>
}
