import { useEffect, useState } from 'react'
import { ApiError, apiRequest } from '../api/client'
import { RouteLink } from '../routing/Router'
import { EmptyState } from '../components/common/EmptyState'

type RecordResult = { id: number; lead_number?: string; deal_name?: string; requirement_id?: number; deal_status?: string }
export function ConversionResultPage({ kind, id }: { kind: 'leads' | 'deals'; id: number }) {
  const [data, setData] = useState<RecordResult | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  useEffect(() => {
    let active = true
    setData(null); setError(null)
    apiRequest<RecordResult>(`/${kind}/${id}`).then(value => { if (active) setData(value) }).catch((reason: unknown) => { if (active) setError(reason instanceof ApiError ? reason : new ApiError(undefined, 'Unable to load result.')) })
    return () => { active = false }
  }, [kind, id])
  return <main className="dashboard"><RouteLink to="/requirement-intelligence">Back to Requirements</RouteLink>{error ? <EmptyState title={error.kind === 'forbidden' ? 'Access is not permitted' : error.kind === 'not-found' ? 'Record not found' : error.kind === 'authentication' ? 'Authentication required' : 'Unable to load record'}>Return to Requirements or retry after checking your session and connection.</EmptyState> : !data ? <p>Loading record...</p> : <section className="panel"><h2>{data.deal_name || data.lead_number}</h2><p>{kind === 'deals' ? 'Deal' : 'Lead'} #{data.id}</p>{data.deal_status && <p>{data.deal_status}</p>}{data.requirement_id && <RouteLink to={`/requirement-intelligence/${data.requirement_id}`}>View Requirement #{data.requirement_id}</RouteLink>}</section>}</main>
}
