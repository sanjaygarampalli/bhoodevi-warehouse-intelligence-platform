import { useEffect, useRef, useState, type FormEvent } from 'react'
import { apiRequest, ApiError } from '../api/client'
import { getAuthenticatedContext } from '../api/organizationContext'
import type { RequirementEvidence } from '../api/requirementIntelligence'

export function RequirementEvidenceControls({ requirementId, organizationId, evidence, onSaved }: {
  requirementId: number; organizationId: number; evidence: RequirementEvidence[]; onSaved: () => void
}) {
  const [canWrite, setCanWrite] = useState(false)
  const [source, setSource] = useState('')
  const [observed, setObserved] = useState('')
  const [inference, setInference] = useState('')
  const [classification, setClassification] = useState('UNKNOWN')
  const [sourceUrl, setSourceUrl] = useState('')
  const [evidenceDate, setEvidenceDate] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const submitting = useRef(false)
  useEffect(() => {
    let active = true
    getAuthenticatedContext().then((context) => {
      if (active) setCanWrite(context.user.role === 'admin' || context.organizations.some((org) => org.organization_id === organizationId && ['OWNER', 'ADMIN', 'MANAGER', 'MEMBER'].includes(org.role)))
    }).catch(() => { if (active) setMessage('Evidence permissions could not be loaded.') })
    return () => { active = false }
  }, [organizationId])
  async function save(path: string, method: string, payload: object) {
    if (submitting.current) return
    submitting.current = true; setBusy(true); setMessage('')
    try {
      await apiRequest(path, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      setMessage('Evidence saved.'); onSaved()
    } catch (error: unknown) { setMessage(error instanceof ApiError ? error.message : 'Evidence could not be saved.') }
    finally { submitting.current = false; setBusy(false) }
  }
  function add(event: FormEvent) {
    event.preventDefault()
    void save(`/requirement-intelligence/${requirementId}/evidence`, 'POST', {
      source, observed_evidence: observed, inference: inference || null, classification,
      source_url: sourceUrl || null, evidence_date: evidenceDate ? new Date(evidenceDate).toISOString() : null,
      verification_status: 'UNVERIFIED',
    })
  }
  return <div className="evidence-controls">
    {canWrite && <><form onSubmit={add} className="conversion-form">
      <label>Source<input required maxLength={255} value={source} onChange={(event) => setSource(event.target.value)} /></label>
      <label>Observed evidence<textarea required value={observed} onChange={(event) => setObserved(event.target.value)} /></label>
      <label>Inference<textarea value={inference} onChange={(event) => setInference(event.target.value)} /></label>
      <label>Classification<select value={classification} onChange={(event) => setClassification(event.target.value)}><option>UNKNOWN</option><option>FACT</option><option>INFERENCE</option></select></label>
      <label>Source URL<input type="url" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} /></label>
      <label>Evidence date<input type="datetime-local" value={evidenceDate} onChange={(event) => setEvidenceDate(event.target.value)} /></label>
      <button className="action-button" disabled={busy}>Add unverified evidence</button>
    </form><p className="search-note">Classification and verification are separate. Review the original source before verifying evidence.</p>
    {evidence.filter((item) => item.verification_status !== 'REJECTED').map((item) => <div className="conversion-form" key={item.id}><strong>{item.source}</strong>
      {item.verification_status === 'UNVERIFIED' && <button disabled={busy} onClick={() => void save(`/requirement-intelligence/${requirementId}/evidence/${item.id}`, 'PATCH', { verification_status: 'REVIEWED' })}>Mark reviewed</button>}
      {item.verification_status === 'REVIEWED' && <button disabled={busy} onClick={() => { if (window.confirm('Verify this evidence after checking its original source?')) void save(`/requirement-intelligence/${requirementId}/evidence/${item.id}`, 'PATCH', { verification_status: 'VERIFIED' }) }}>Verify evidence</button>}
      <button disabled={busy} onClick={() => { if (window.confirm('Reject this evidence? Its recorded verification provenance will be retained.')) void save(`/requirement-intelligence/${requirementId}/evidence/${item.id}`, 'PATCH', { verification_status: 'REJECTED' }) }}>Reject evidence</button>
    </div>)}</>}
    {message && <p role="status">{message}</p>}
  </div>
}
