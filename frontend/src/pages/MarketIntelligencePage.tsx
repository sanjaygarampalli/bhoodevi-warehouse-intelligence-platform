import { useEffect, useMemo, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { getAuthenticatedContext, type OrganizationContext } from '../api/organizationContext'
import { convertRequirementCandidate, getMarketSignal, getSignalAssessment, listMarketSignals, listRequirementCandidates, listSignalEvidence, type MarketSignal, type MarketSignalAssessment, type MarketSignalEvidence, type RequirementCandidate } from '../api/marketIntelligence'
import { EmptyState } from '../components/common/EmptyState'
import { SectionHeader } from '../components/common/SectionHeader'
import { RouteLink } from '../routing/Router'
import { SourceLink } from '../components/common/SourceLink'
import { MarketReviewControls } from '../components/MarketReviewControls'
import { useOrganizationWrite } from '../hooks/useOrganizationWrite'

function errorMessage(error: ApiError) { return error.kind === 'authentication' ? 'Authentication required' : error.kind === 'forbidden' ? 'You do not have permission to access this intelligence.' : error.kind === 'network' ? 'Unable to connect to the BWIP backend.' : 'BWIP backend returned an error.' }
function label(value: string) { return value.replaceAll('_', ' ') }
function date(value: string) { return new Date(value).toLocaleDateString() }
function dateTime(value: string) { return new Date(value).toLocaleString() }

type DetailData = { signal: MarketSignal; evidence: MarketSignalEvidence[]; assessment: MarketSignalAssessment; requirement: RequirementCandidate | null }

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="panel market-detail-section"><p className="section-kicker">BWIP intelligence</p><h3>{title}</h3>{children}</section>
}

function CandidateConversion({ candidate }: { candidate: RequirementCandidate }) {
  const canWrite = useOrganizationWrite(candidate.organization_id)
  const [leadNumber, setLeadNumber] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const submitting = useRef(false)
  const [result, setResult] = useState<{ lead: { id: number }; requirement: { id: number } } | null>(null)
  async function convert() {
    if (submitting.current || result || !leadNumber.trim() || !['ACCEPTED', 'CONVERTED'].includes(candidate.status)) return
    if (!window.confirm('This creates a Lead and Requirement from the accepted candidate. Continue?')) return
    submitting.current = true
    setBusy(true); setMessage('')
    try {
      const result = await convertRequirementCandidate(candidate.id, { lead_number: leadNumber.trim(), requirement_title: candidate.summary, requirement_description: candidate.reasoning })
      setResult(result)
      setMessage(result.created ? `Lead ${result.lead.id} and Requirement ${result.requirement.id} created.` : `Existing Requirement ${result.requirement.id} returned; no duplicate was created.`)
    } catch (reason: unknown) {
      const error = reason instanceof ApiError ? reason : new ApiError(undefined, 'Conversion failed.')
      setMessage(error.kind === 'authentication' ? 'Your session has expired. Sign in again to continue.' : error.kind === 'forbidden' ? 'You do not have write access to this organization.' : error.status === 409 ? 'This candidate has already been converted or is not currently eligible.' : error.kind === 'validation' ? 'Check the lead number and try again.' : error.kind === 'network' ? 'The BWIP backend could not be reached.' : error.message)
    } finally { submitting.current = false; setBusy(false) }
  }
  return <DetailSection title="Candidate conversion"><p>{label(candidate.status)} · {label(candidate.confidence_level)} confidence</p><p>{candidate.reasoning}</p>{canWrite && ['ACCEPTED', 'CONVERTED'].includes(candidate.status) && !result ? <div className="conversion-form"><label>Lead number<input value={leadNumber} onChange={(event) => setLeadNumber(event.target.value)} placeholder="Enter a Lead number" /></label><button className="action-button" disabled={busy || !leadNumber.trim()} onClick={convert}>{busy ? 'Converting…' : 'Convert to Lead + Requirement'}</button></div> : <small className="conversion-note">{canWrite ? 'Only an explicitly accepted candidate can be converted.' : 'Organization write permission is required to convert this candidate.'}</small>}{message && <p className="action-message" role="status">{message}</p>}{result && <p><RouteLink to={`/leads/${result.lead.id}`}>View Lead #{result.lead.id}</RouteLink> · <RouteLink to={`/requirement-intelligence/${result.requirement.id}`}>View Requirement #{result.requirement.id}</RouteLink></p>}</DetailSection>
}

function DetailPage({ signalId }: { signalId: string }) {
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<DetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)
  const numericId = /^\d+$/.test(signalId) ? Number(signalId) : null

  useEffect(() => {
    let active = true
    setData(null); setError(null); setLoading(true)
    if (numericId === null || numericId < 1) {
      setError(new ApiError(404, 'Market signal not found'))
      setLoading(false)
      return () => { active = false }
    }
    Promise.all([getMarketSignal(numericId), listSignalEvidence(numericId), getSignalAssessment(numericId)])
      .then(async ([signal, evidence, assessment]) => {
        let requirement: RequirementCandidate | null = null
        try {
          const candidates = await listRequirementCandidates(signal.organization_id)
          requirement = candidates.find((candidate) => candidate.market_signal_id === signal.id) ?? null
        } catch (reason: unknown) {
          // A failed supplementary lookup is an error, not an empty requirement result.
          throw reason
        }
        if (active) setData({ signal, evidence, assessment, requirement })
      })
      .catch((reason: unknown) => { if (active) setError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load market signal detail.')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [numericId, revision])

  if (loading) return <main className="dashboard market-page"><RouteLink className="back-link" to="/market-intelligence">← Back to Market Intelligence</RouteLink><EmptyState title="Loading market signal detail...">Retrieving the signal, evidence, and assessment from the backend.</EmptyState></main>
  if (error || !data) {
    const title = error?.kind === 'authentication' ? 'Authentication required' : error?.kind === 'forbidden' ? 'Access to this market signal is not permitted.' : error?.kind === 'not-found' ? 'Market signal not found.' : error?.kind === 'network' ? 'Unable to connect to the BWIP backend.' : 'Market signal detail could not be loaded.'
    return <main className="dashboard market-page"><RouteLink className="back-link" to="/market-intelligence">← Back to Market Intelligence</RouteLink><EmptyState title={title}>The backend response was not replaced with sample intelligence.</EmptyState></main>
  }

  const { signal, evidence, assessment, requirement } = data
  return <main className="dashboard market-page"><RouteLink className="back-link" to="/market-intelligence">â† Back to Market Intelligence</RouteLink><header className="market-detail-heading"><div><p className="section-kicker">Market signal detail</p><h2>{signal.title}</h2><p>{label(signal.signal_type)} Â· {label(signal.status)}</p></div><span className="status-chip">{label(signal.confidence_level)} confidence</span></header><DetailSection title="Signal overview"><dl className="detail-list"><div><dt>Description</dt><dd>{signal.description || 'Not available'}</dd></div><div><dt>Signal type</dt><dd>{label(signal.signal_type)}</dd></div><div><dt>Status</dt><dd>{label(signal.status)}</dd></div><div><dt>Confidence</dt><dd>{label(signal.confidence_level)}</dd></div><div><dt>Geography</dt><dd>{[signal.location_text, signal.city, signal.district, signal.state, signal.country].filter(Boolean).join(', ') || 'Not available'}</dd></div><div><dt>Detected</dt><dd>{dateTime(signal.detected_at)}</dd></div><div><dt>Source / provenance</dt><dd>{[signal.source_name, label(signal.source_type)].filter(Boolean).join(' Â· ')}</dd></div></dl></DetailSection><DetailSection title="Observed evidence"><div className="market-evidence">{evidence.length ? evidence.map((item) => <article className="evidence-item" key={item.id}><strong>{item.title}</strong><small>{[item.source_name, label(item.evidence_type), label(item.credibility_level)].filter(Boolean).join(' Â· ')}</small>{item.excerpt && <p>{item.excerpt}</p>}{item.source_url && <SourceLink url={item.source_url} />}</article>) : <p>Evidence not available.</p>}</div></DetailSection><div className="market-detail-grid"><DetailSection title="Inference"><p>{assessment.inference || assessment.explanation}</p>{assessment.reasons.length > 0 && <ul>{assessment.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>}</DetailSection><DetailSection title="Recommendation"><p>{assessment.recommendation || assessment.recommended_next_step}</p></DetailSection></div><DetailSection title="Confidence"><p>{label(assessment.confidence_level)} confidence Â· {label(assessment.demand_strength)} demand strength</p><p>{assessment.indicates_potential_warehouse_demand ? 'The assessment indicates potential warehouse demand.' : 'The assessment does not indicate potential warehouse demand.'}</p></DetailSection><div className="market-related"><DetailSection title="Related company">{signal.company_id ? <RouteLink className="text-link" to={`/companies/${signal.company_id}`}>Open company profile â†’</RouteLink> : <p>No related company identified.</p>}</DetailSection>{requirement ? <CandidateConversion candidate={requirement} /> : <DetailSection title="Requirement candidate"><p>No candidate is linked to this market signal.</p></DetailSection>}</div><MarketReviewControls signal={signal} candidate={requirement} onSaved={() => setRevision((value) => value + 1)} /><DetailSection title="Review state"><dl className="detail-list"><div><dt>Status</dt><dd>{label(signal.status)}</dd></div><div><dt>Reviewed</dt><dd>{signal.reviewed_at ? dateTime(signal.reviewed_at) : 'Not reviewed'}</dd></div>{signal.review_notes && <div><dt>Review notes</dt><dd>{signal.review_notes}</dd></div>}</dl></DetailSection></main>
}

export function MarketIntelligencePage({ signalId }: { signalId?: string }) {
  const [organizations, setOrganizations] = useState<OrganizationContext[]>([])
  const [organizationId, setOrganizationId] = useState<number | null>(null)
  const [signals, setSignals] = useState<MarketSignal[]>([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    let active = true
    if (!signalId) getAuthenticatedContext().then((context) => {
      if (!active) return
      setOrganizations(context.organizations)
      if (context.organizations.length === 1) setOrganizationId(context.organizations[0].organization_id)
      else setLoading(false)
    }).catch((reason: unknown) => {
      if (active) { setError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load market intelligence.')); setLoading(false) }
    })
    return () => { active = false }
  }, [signalId])
  useEffect(() => {
    let active = true
    setSignals([])
    if (signalId || organizationId === null) return () => { active = false }
    setLoading(true); setError(null)
    listMarketSignals(organizationId).then((rows) => { if (active) setSignals(rows) })
      .catch((reason: unknown) => { if (active) setError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load market intelligence.')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [signalId, organizationId])
  const visible = useMemo(() => { const term = query.trim().toLowerCase(); return signals.filter((signal) => (status === 'ALL' || signal.status === status) && (!term || [signal.title, signal.description, signal.signal_type, signal.source_name, signal.city, signal.state].some((value) => value?.toLowerCase().includes(term)))) }, [signals, query, status])
  if (signalId) return <DetailPage signalId={signalId} />
  return <main className="dashboard market-page"><section className="company-intro"><div><p className="section-kicker">Evidence-led intelligence</p><h2>Market Intelligence</h2><p>Review verified market signals that may indicate potential warehouse demand.</p></div><span className="record-count">{signals.length} loaded signal{signals.length === 1 ? '' : 's'}</span></section><section className="panel company-search-panel"><SectionHeader kicker="Discovery" title="Search loaded signals" />{organizations.length > 1 && <label>Organization <select value={organizationId ?? ''} onChange={(event) => { setSignals([]); setError(null); setLoading(true); setOrganizationId(Number(event.target.value)) }} aria-label="Select organization"><option value="" disabled>Select an organization</option>{organizations.map((organization) => <option value={organization.organization_id} key={organization.organization_id}>{organization.trading_name || organization.legal_name}</option>)}</select></label>}<div className="market-filters"><label className="company-search"><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search title, source, type, geography..." aria-label="Search loaded market signals" /></label><select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filter by signal status"><option value="ALL">All statuses</option>{['DETECTED', 'UNDER_REVIEW', 'VERIFIED', 'REJECTED', 'ARCHIVED'].map((item) => <option value={item} key={item}>{label(item)}</option>)}</select></div></section>{loading ? <p>Loading market intelligence...</p> : error ? <EmptyState title={errorMessage(error)}>The backend response was not replaced with sample intelligence.</EmptyState> : !organizations.length ? <EmptyState title="No active organization context">Market Intelligence requires an active organization membership.</EmptyState> : organizations.length > 1 && organizationId === null ? <EmptyState title="Select an organization">Choose an authorized organization to load Market Intelligence.</EmptyState> : !visible.length ? <EmptyState title={query || status !== 'ALL' ? 'No market signals match your filters.' : 'No market signals yet'}>No market signals were returned for the selected organization.</EmptyState> : <section className="market-list" aria-label="Market signals">{visible.map((signal) => <RouteLink className="market-card" to={`/market-intelligence/${signal.id}`} key={signal.id}><div><p className="section-kicker">{label(signal.signal_type)}</p><h3>{signal.title}</h3><p>{signal.description || 'No description supplied.'}</p></div><div className="market-card-meta"><span>{label(signal.status)}</span><strong>{label(signal.confidence_level)}</strong><small>{date(signal.detected_at)}</small></div></RouteLink>)}</section>}</main>
}
