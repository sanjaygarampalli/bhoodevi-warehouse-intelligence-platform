import { useEffect, useState } from 'react'
import { apiRequest, ApiError } from '../api/client'
import { getAuthenticatedContext, type OrganizationContext } from '../api/organizationContext'
import { EmptyState } from '../components/common/EmptyState'
import { SectionHeader } from '../components/common/SectionHeader'
import { KpiCard } from '../components/dashboard/KpiCard'
import { RouteLink } from '../routing/Router'

type Dashboard = {
  generated_at: string
  executive_summary: { total_active_leads: number; high_priority_leads: number; critical_priority_leads: number; active_opportunities: number; overdue_follow_ups: number; follow_ups_due_today: number }
  top_priorities: Array<{ entity_type: string; entity_id: number; name: string; reason: string; recommended_action: string; priority_score: number }>
  todays_attention: Array<{ entity_type: string; entity_id: number; title: string; reason: string; recommended_action: string }>
}

export function CommandCenter() {
  const [organizations, setOrganizations] = useState<OrganizationContext[]>([])
  const [organizationId, setOrganizationId] = useState<number | null>(null)
  const [data, setData] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    getAuthenticatedContext().then((context) => {
      if (!active) return
      setOrganizations(context.organizations)
      if (context.organizations.length === 1) setOrganizationId(context.organizations[0].organization_id)
      setLoading(false)
    }).catch(() => { if (active) { setError('Organization context could not be loaded.'); setLoading(false) } })
    return () => { active = false }
  }, [])
  useEffect(() => {
    if (organizationId === null) return
    let active = true
    setData(null); setError(null); setLoading(true)
    apiRequest<Dashboard>(`/operational-dashboard?organization_id=${organizationId}`).then((result) => { if (active) setData(result) })
      .catch((reason: unknown) => { if (active) setError(reason instanceof ApiError ? reason.message : 'Dashboard could not be loaded.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [organizationId])
  const summary = data?.executive_summary
  return <main className="dashboard" id="command-center">
    <section className="welcome-row"><div><p className="section-kicker">Today's operating view</p><h2>See what needs your attention.</h2></div>
      {organizations.length > 1 && <label>Organization <select aria-label="Dashboard organization" value={organizationId ?? ''} onChange={(event) => { setData(null); setOrganizationId(Number(event.target.value)) }}><option value="" disabled>Select an organization</option>{organizations.map((org) => <option key={org.organization_id} value={org.organization_id}>{org.trading_name || org.legal_name}</option>)}</select></label>}
    </section>
    {loading ? <p role="status">Loading operational intelligence...</p> : error ? <EmptyState title="Dashboard unavailable">{error}</EmptyState> : organizationId === null ? <EmptyState title={organizations.length ? 'Select an organization' : 'No active organization context'}>Choose an active organization to load operational intelligence.</EmptyState> : data && <>
      <p className="search-note">Calculated {new Date(data.generated_at).toLocaleString()}. Recommendations require human review.</p>
      <section className="kpi-grid" aria-label="Command Center metrics">
        <KpiCard label="Active leads" value={summary!.total_active_leads} detail="Current organization" />
        <KpiCard label="Active opportunities" value={summary!.active_opportunities} detail="Current organization" />
        <KpiCard label="High-priority leads" value={summary!.high_priority_leads + summary!.critical_priority_leads} detail="High and critical recommendations" />
        <KpiCard label="Follow-ups needing attention" value={summary!.overdue_follow_ups + summary!.follow_ups_due_today} detail="Overdue and due today" />
      </section>
      <div className="dashboard-grid"><section className="panel"><SectionHeader kicker="Focus area" title="Priority opportunities" />
        {data.top_priorities.length ? data.top_priorities.map((item) => <article key={`${item.entity_type}-${item.entity_id}`}><RouteLink to={`/${item.entity_type === 'lead' ? 'leads' : 'deals'}/${item.entity_id}`}>{item.name}</RouteLink><p>{item.reason}</p><small>{item.recommended_action.replaceAll('_', ' ')} · score {item.priority_score}</small></article>) : <EmptyState title="No priority items">No priority items were returned for this organization.</EmptyState>}
      </section><section className="panel"><SectionHeader kicker="Work queue" title="Today's attention" />
        {data.todays_attention.length ? data.todays_attention.map((item) => <article key={`${item.entity_type}-${item.entity_id}`}><strong>{item.title}</strong><p>{item.reason}</p><small>{item.recommended_action.replaceAll('_', ' ')}</small></article>) : <EmptyState title="No attention items">No attention items were returned for this organization.</EmptyState>}
      </section></div>
      <p><RouteLink to="/market-intelligence">Review market signals</RouteLink> · <RouteLink to="/f5/companies">Discover companies</RouteLink> · <RouteLink to="/requirement-intelligence">Review requirements</RouteLink></p>
    </>}
  </main>
}
