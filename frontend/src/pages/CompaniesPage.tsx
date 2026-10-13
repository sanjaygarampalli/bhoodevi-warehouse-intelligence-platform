import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../api/client'
import { listCompanies, type Company } from '../api/companies'
import { EmptyState } from '../components/common/EmptyState'
import { SectionHeader } from '../components/common/SectionHeader'
import { RouteLink } from '../routing/Router'

function LoadState({ error }: { error: ApiError }) {
  const message = error.kind === 'authentication'
    ? 'Sign-in required to view company intelligence.'
    : error.kind === 'forbidden'
      ? 'Access to this company intelligence is not permitted.'
      : error.kind === 'not-found'
        ? 'Company record not found.'
        : error.kind === 'network'
          ? 'Unable to connect to the BWIP backend.'
          : 'Company intelligence could not be loaded.'
  return <EmptyState title={message}>No records were substituted. Connect an authenticated BWIP session and try again.</EmptyState>
}

export function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)
  useEffect(() => { listCompanies().then(setCompanies).catch((reason: unknown) => setError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load companies.'))).finally(() => setLoading(false)) }, [])
  const visible = useMemo(() => { const term = query.trim().toLowerCase(); return term ? companies.filter((company) => [company.company_name, company.industry, company.company_type, company.headquarters_city, company.headquarters_state, company.headquarters_country].some((value) => value?.toLowerCase().includes(term))) : companies }, [companies, query])
  return <main className="dashboard companies-page"><section className="company-intro"><div><p className="section-kicker">Company intelligence</p><h2>Companies</h2><p>Discover, verify, and understand companies that may create warehouse demand.</p></div><span className="record-count">{companies.length} loaded record{companies.length === 1 ? '' : 's'}</span></section><section className="panel company-search-panel"><SectionHeader kicker="Discovery" title="Search company records" /><label className="company-search"><span aria-hidden="true">⌕</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name, industry, location..." aria-label="Search loaded company records" />{query && <button type="button" onClick={() => setQuery('')}>Clear</button>}</label><p className="search-note">Search applies to the company records returned by the backend. No unsupported server-side filters are applied.</p></section><section className="company-results"><div className="results-heading"><div><p className="section-kicker">Records</p><h3>{query ? `${visible.length} matching compan${visible.length === 1 ? 'y' : 'ies'}` : 'All companies'}</h3></div></div>{loading && <EmptyState title="Loading company intelligence...">Retrieving organization-scoped company records from BWIP.</EmptyState>}{!loading && error && <LoadState error={error} />}{!loading && !error && visible.length === 0 && <EmptyState title={query ? 'No companies match your search.' : 'No company records are available.'}>{query ? 'Try a broader search or clear the search term.' : 'Company records will appear here when they are available to your organization.'}</EmptyState>}{!loading && !error && visible.length > 0 && <div className="company-list">{visible.map((company) => <RouteLink className="company-card" to={`/companies/${company.id}`} key={company.id}><div><h3>{company.company_name}</h3><p>{company.industry || 'Industry not available'} · {company.company_type || 'Type not available'}</p><p className="company-location">{[company.headquarters_city, company.headquarters_state, company.headquarters_country].filter(Boolean).join(', ') || 'Location not available'}</p></div><div className="company-card-meta"><span>{company.business_status || 'Status not available'}</span><strong>View intelligence&nbsp; →</strong></div></RouteLink>)}</div>}</section></main>
}