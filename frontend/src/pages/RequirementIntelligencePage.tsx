import { useEffect, useMemo, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { getAuthenticatedContext, type OrganizationContext } from '../api/organizationContext'
import { convertWarehouseMatch, getRequirementIntelligence, listRequirementIntelligence, listWarehouseMatches, type RequirementIntelligence, type WarehouseMatch } from '../api/requirementIntelligence'
import { EmptyState } from '../components/common/EmptyState'
import { SectionHeader } from '../components/common/SectionHeader'
import { RouteLink } from '../routing/Router'
import { RequirementEvidenceControls } from '../components/RequirementEvidenceControls'
import { useOrganizationWrite } from '../hooks/useOrganizationWrite'

function label(value: string | null | undefined) { return value ? value.replaceAll('_', ' ') : 'Unknown' }
function date(value: string | null | undefined) { return value ? new Date(value).toLocaleDateString() : 'Unknown' }
function errorTitle(error: ApiError | null) {
  if (error?.kind === 'authentication') return 'Authentication required'
  if (error?.kind === 'forbidden') return 'Requirement access is not permitted'
  if (error?.kind === 'not-found') return 'Requirement not found'
  if (error?.kind === 'network') return 'Unable to connect to BWIP'
  return 'Requirement intelligence could not be loaded'
}
function actionError(error: ApiError) {
  if (error.kind === 'authentication') return 'Your session has expired. Sign in again to continue.'
  if (error.kind === 'forbidden') return 'You do not have write access to this organization.'
  if (error.status === 409) return 'This match is no longer eligible or has already been converted.'
  if (error.kind === 'validation') return 'Check the required conversion fields and try again.'
  if (error.kind === 'network') return 'The BWIP backend could not be reached.'
  return error.message || 'The conversion could not be completed.'
}

function EvidenceCard({ item }: { item: RequirementIntelligence['evidence'][number] }) {
  return <article className="requirement-evidence"><div className="requirement-evidence-heading"><span className={`evidence-classification evidence-${item.classification.toLowerCase()}`}>{item.classification}</span><strong>{item.source}</strong><span>{label(item.verification_status)}</span></div><p>{item.observed_evidence}</p>{item.inference && <small>Inference: {item.inference}</small>}<footer>{date(item.evidence_date)} · confidence {item.confidence ?? 'Unknown'}</footer></article>
}

function MatchCard({ match, requirementId, organizationId }: { match: WarehouseMatch; requirementId: number; organizationId: number }) {
  const canWrite = useOrganizationWrite(organizationId)
  const [dealName, setDealName] = useState('')
  const [stageId, setStageId] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const submitting = useRef(false)
  const [dealId, setDealId] = useState<number | null>(null)
  const eligible = !['REJECTED', 'STALE', 'CONVERTED'].includes(match.status)
  async function convert() {
    if (submitting.current || dealId !== null || !dealName.trim() || !Number.isSafeInteger(Number(stageId)) || Number(stageId) < 1 || !eligible) return
    if (!window.confirm('This creates a commercial Deal from the selected warehouse match. Continue?')) return
    submitting.current = true
    setBusy(true); setMessage('')
    try {
      const result = await convertWarehouseMatch(match.id, { deal_name: dealName.trim(), requirement_id: requirementId, stage_id: Number(stageId) })
      setDealId(result.deal.id)
      setMessage(result.created ? `Deal ${result.deal.id} created.` : `Existing Deal ${result.deal.id} returned; no duplicate was created.`)
    } catch (reason: unknown) {
      setMessage(actionError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Conversion failed.')))
    } finally { submitting.current = false; setBusy(false) }
  }
  return <article className="warehouse-match-card"><div className="warehouse-match-summary"><strong>Warehouse #{match.warehouse_id}</strong><span>{label(match.status)} · {label(match.match_level)}</span><b>{match.match_score}</b></div><p>{match.requirement_compatibility || match.top_reason || 'No compatibility explanation supplied.'}</p><small>Lead #{match.lead_id}{match.match_rank ? ` · rank ${match.match_rank}` : ''}{match.capacity_fit !== null ? ` · capacity fit ${match.capacity_fit}` : ''}</small>{canWrite && eligible && dealId === null ? <div className="conversion-form"><label>Deal name<input value={dealName} onChange={(event) => setDealName(event.target.value)} placeholder="Enter a Deal name" /></label><label>Pipeline stage ID<input inputMode="numeric" value={stageId} onChange={(event) => setStageId(event.target.value)} placeholder="Required by the backend" /></label><button className="action-button" disabled={busy || !dealName.trim() || !Number.isSafeInteger(Number(stageId)) || Number(stageId) < 1} onClick={convert}>{busy ? 'Converting…' : 'Convert to Deal'}</button></div> : <small className="conversion-note">{canWrite ? 'This match is not eligible for conversion in its current lifecycle state.' : 'Organization write permission is required to convert this match.'}</small>}{message && <p className="action-message" role="status">{message}</p>}{dealId !== null && <RouteLink to={`/deals/${dealId}`}>View Deal #{dealId}</RouteLink>}</article>
}

function DetailPage({ id }: { id: number }) {
  const [version, setVersion] = useState(0)
  const [data, setData] = useState<RequirementIntelligence | null>(null)
  const [matches, setMatches] = useState<WarehouseMatch[]>([])
  const [error, setError] = useState<ApiError | null>(null)
  const [matchError, setMatchError] = useState<ApiError | null>(null)
  useEffect(() => {
    let active = true
    setData(null); setMatches([]); setError(null); setMatchError(null)
    getRequirementIntelligence(id).then((result) => active && setData(result)).catch((reason: unknown) => active && setError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load requirement detail.')))
    listWarehouseMatches(id).then((result) => active && setMatches(result)).catch((reason: unknown) => active && setMatchError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load warehouse matches.')))
    return () => { active = false }
  }, [id, version])
  if (error) return <main className="dashboard requirement-page"><RouteLink className="back-link" to="/requirement-intelligence">← Back to Requirements</RouteLink><EmptyState title={errorTitle(error)}>The backend response was not replaced with sample demand.</EmptyState></main>
  if (!data) return <main className="dashboard requirement-page"><RouteLink className="back-link" to="/requirement-intelligence">← Back to Requirements</RouteLink><EmptyState title="Loading requirement intelligence...">Retrieving demand, evidence, assessment, and match context.</EmptyState></main>
  const requirement = data.requirement
  const assessment = data.assessment
  return <main className="dashboard requirement-page"><RouteLink className="back-link" to="/requirement-intelligence">← Back to Requirements</RouteLink><section className="company-profile-header"><div><p className="section-kicker">Requirement intelligence</p><h2>{requirement.title}</h2><p>{data.company_name} · {label(requirement.requirement_status)}</p></div><span className="status-chip">{assessment?.freshness ?? 'UNKNOWN'}</span></section><div className="requirement-detail-grid"><section className="panel"><SectionHeader kicker="Demand" title="What is required" /><dl className="detail-list"><dt>Geography</dt><dd>{[requirement.preferred_locality, requirement.preferred_city, requirement.preferred_state].filter(Boolean).join(', ') || 'Unknown'}{requirement.radius_km ? ` · ${requirement.radius_km} km radius` : ''}</dd><dt>Area</dt><dd>{requirement.minimum_area ?? requirement.required_builtup_area ?? 'Unknown'}{requirement.maximum_area ? `–${requirement.maximum_area}` : ''} sq ft</dd><dt>Warehouse type</dt><dd>{label(requirement.warehouse_type)}</dd><dt>Timing</dt><dd>{label(requirement.move_in_timeframe)}</dd><dt>Commercial</dt><dd>{requirement.budget_per_sqft ?? 'Unknown'} budget · {requirement.lease_duration_months ?? 'Unknown'} months</dd></dl></section><section className="panel"><SectionHeader kicker="Assessment" title="Explainable confidence" />{assessment ? <><strong className="assessment-score">{assessment.requirement_confidence ?? 'Unknown'}<small>/ 100</small></strong><p>{assessment.reasons.join(' · ') || 'No assessment reasons supplied.'}</p><p className="freshness-line">Freshness: <strong>{assessment.freshness}</strong> · anchored {date(assessment.freshness_anchor)}</p><dl className="confidence-list"><dt>Geography</dt><dd>{assessment.geography_confidence ?? 'Unknown'}</dd><dt>Size</dt><dd>{assessment.size_confidence ?? 'Unknown'}</dd><dt>Timing</dt><dd>{assessment.timing_confidence ?? 'Unknown'}</dd><dt>Operational</dt><dd>{assessment.operational_confidence ?? 'Unknown'}</dd><dt>Commercial</dt><dd>{assessment.commercial_confidence ?? 'Unknown'}</dd><dt>Evidence strength</dt><dd>{assessment.evidence_strength ?? 'Unknown'}</dd></dl></> : <p>No assessment is available yet.</p>}</section><section className="panel"><SectionHeader kicker="Provenance" title="Requirement evidence" /><RequirementEvidenceControls requirementId={id} organizationId={data.organization_id} evidence={data.evidence} onSaved={() => setVersion((value) => value + 1)} />{data.evidence.length ? <div className="requirement-evidence-list">{data.evidence.map((item) => <EvidenceCard item={item} key={item.id} />)}</div> : <EmptyState title="No requirement evidence">No evidence has been recorded for this requirement.</EmptyState>}</section><section className="panel"><SectionHeader kicker="Warehouse intelligence" title="Compatible warehouse matches" />{matchError ? <EmptyState title="Warehouse matches could not be loaded">{actionError(matchError)}</EmptyState> : matches.length ? <div className="warehouse-match-list">{matches.map((match) => <MatchCard match={match} requirementId={requirement.id} organizationId={data.organization_id} key={match.id} />)}</div> : <EmptyState title="No warehouse matches">No persisted warehouse matches were returned for this requirement.</EmptyState>}<small className="provenance-note">Supporting market signal IDs: {data.market_signal_ids.length ? data.market_signal_ids.join(', ') : 'none recorded; no candidate-to-requirement relationship is fabricated.'}</small></section></div></main>
}

export function RequirementIntelligencePage({ requirementId }: { requirementId?: string }) {
  const numericId = requirementId && /^\d+$/.test(requirementId) ? Number(requirementId) : null
  const [organizations, setOrganizations] = useState<OrganizationContext[]>([])
  const [organizationId, setOrganizationId] = useState<number | null>(null)
  const [requirements, setRequirements] = useState<RequirementIntelligence[]>([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)
  useEffect(() => { if (numericId !== null) return; let active = true; getAuthenticatedContext().then((context) => { if (!active) return; setOrganizations(context.organizations); if (context.organizations.length === 1) setOrganizationId(context.organizations[0].organization_id); setLoading(false) }).catch((reason: unknown) => { if (active) { setError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load requirement intelligence.')); setLoading(false) } }); return () => { active = false } }, [numericId])
  useEffect(() => { if (numericId !== null || organizationId === null) return; let active = true; setRequirements([]); setError(null); setLoading(true); const timer = window.setTimeout(() => listRequirementIntelligence(organizationId, query, status).then((items) => active && setRequirements(items)).catch((reason: unknown) => active && setError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load requirements.'))).finally(() => active && setLoading(false)), 180); return () => { active = false; window.clearTimeout(timer) } }, [numericId, organizationId, query, status])
  const counts = useMemo(() => ({ total: requirements.length, needsVerification: requirements.filter((item) => (!item.evidence.length || item.evidence.some((evidence) => evidence.verification_status !== 'VERIFIED'))).length, highConfidence: requirements.filter((item) => Number(item.assessment?.requirement_confidence ?? 0) >= 70).length, stale: requirements.filter((item) => item.assessment?.freshness === 'STALE').length }), [requirements])
  if (numericId !== null) return <DetailPage id={numericId} key={numericId} />
  return <main className="dashboard requirement-page"><section className="company-intro"><div><p className="section-kicker">F6 · Evidence-led demand</p><h2>Requirement Intelligence</h2><p>Discover, qualify, and explain genuine warehouse demand without collapsing inference into fact.</p></div><span className="record-count">{counts.total} loaded requirement{counts.total === 1 ? '' : 's'}</span></section><section className="requirement-kpi-grid"><div className="panel"><small>Active view</small><strong>{counts.total}</strong><span>requirements</span></div><div className="panel"><small>Needs verification</small><strong>{counts.needsVerification}</strong><span>evidence review</span></div><div className="panel"><small>High confidence</small><strong>{counts.highConfidence}</strong><span>explainable score ≥70</span></div><div className="panel"><small>Stale</small><strong>{counts.stale}</strong><span>freshness follow-up</span></div></section><section className="panel company-search-panel"><SectionHeader kicker="Discovery" title="Search requirements" />{organizations.length > 1 && <label>Organization <select value={organizationId ?? ''} onChange={(event) => { setRequirements([]); setError(null); setLoading(true); setOrganizationId(Number(event.target.value)) }} aria-label="Select organization"><option value="" disabled>Select an organization</option>{organizations.map((organization) => <option value={organization.organization_id} key={organization.organization_id}>{organization.trading_name || organization.legal_name}</option>)}</select></label>}<div className="market-filters"><label className="company-search"><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search requirement title..." aria-label="Search requirements" /></label><select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filter by requirement status"><option value="ALL">All statuses</option>{['DRAFT', 'ACTIVE', 'ON_HOLD', 'CLOSED', 'CANCELLED'].map((item) => <option value={item} key={item}>{label(item)}</option>)}</select></div></section>{loading ? <p>Loading requirement intelligence...</p> : error ? <EmptyState title={errorTitle(error)}>The backend response was not replaced with fake demand.</EmptyState> : !organizations.length ? <EmptyState title="No active organization context">Requirement Intelligence requires an active organization membership.</EmptyState> : !requirements.length ? <EmptyState title="No requirements match this view">Use the candidate review workflow to create substantiated demand. Empty results are intentional.</EmptyState> : <section className="requirement-list">{requirements.map((item) => <RouteLink className="requirement-card" to={`/requirement-intelligence/${item.requirement.id}`} key={item.requirement.id}><div><p className="section-kicker">{item.company_name}</p><h3>{item.requirement.title}</h3><p>{[item.requirement.preferred_city, item.requirement.preferred_state].filter(Boolean).join(', ') || 'Geography unknown'} · {item.requirement.minimum_area ?? item.requirement.required_builtup_area ?? 'Area unknown'} sq ft</p></div><div className="requirement-card-meta"><span className="f5-chip">{label(item.requirement.requirement_status)}</span><strong>{item.assessment?.requirement_confidence ?? '—'}</strong><small>{item.assessment?.freshness ?? 'UNKNOWN'} · {item.evidence.length} evidence</small></div></RouteLink>)}</section>}</main>
}
