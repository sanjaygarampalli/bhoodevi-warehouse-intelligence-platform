import { apiRequest } from './client'

export type MarketSignal = {
  id: number
  organization_id: number
  company_id: number | null
  title: string
  description: string | null
  signal_type: string
  status: string
  source_type: string
  source_name: string | null
  source_url: string | null
  source_published_at: string | null
  detected_at: string
  location_text: string | null
  city: string | null
  district: string | null
  state: string | null
  country: string | null
  announced_investment_amount: number | string | null
  announced_investment_currency: string | null
  confidence_level: string
  created_by_user_id: number | null
  reviewed_by_user_id: number | null
  reviewed_at: string | null
  review_notes: string | null
  created_at: string
  updated_at: string
}

export type MarketSignalEvidence = {
  id: number
  market_signal_id: number
  evidence_type: string
  source_name: string | null
  source_url: string | null
  title: string
  excerpt: string | null
  published_at: string | null
  recorded_at: string
  credibility_level: string
  created_at: string
  updated_at: string
}

export type MarketSignalAssessment = {
  market_signal_id: number
  indicates_potential_warehouse_demand: boolean
  demand_strength: string
  confidence_level: string
  explanation: string
  reasons: string[]
  recommended_next_step: string
  observed_evidence: string[]
  inference: string
  recommendation: string
}

export type RequirementCandidate = {
  id: number
  organization_id: number
  company_id: number
  market_signal_id: number
  status: string
  demand_strength: string
  confidence_level: string
  summary: string
  reasoning: string
  city: string | null
  district: string | null
  state: string | null
  country: string | null
  created_at: string
  updated_at: string
  reviewed_by_user_id: number | null
  reviewed_at: string | null
}

export type RequirementCandidateConversion = {
  conversion: { id: number; status: string; requirement_candidate_id: number; lead_id: number | null; requirement_id: number | null; created: boolean }
  company: { id: number; company_name: string }
  lead: { id: number; lead_number: string }
  requirement: { id: number; title: string }
  created: boolean
}

export function listMarketSignals(organizationId: number) {
  return apiRequest<MarketSignal[]>(`/market-signals?organization_id=${organizationId}`)
}

export function getMarketSignal(id: number) {
  return apiRequest<MarketSignal>(`/market-signals/${id}`)
}

export function listSignalEvidence(id: number) {
  return apiRequest<MarketSignalEvidence[]>(`/market-signals/${id}/evidence`)
}

export function getSignalAssessment(id: number) {
  return apiRequest<MarketSignalAssessment>(`/market-signals/${id}/assessment`)
}

export function listRequirementCandidates(organizationId: number) {
  return apiRequest<RequirementCandidate[]>(`/requirement-candidates?organization_id=${organizationId}`)
}

export function convertRequirementCandidate(candidateId: number, payload: { lead_number: string; requirement_title?: string; requirement_description?: string }) {
  return apiRequest<RequirementCandidateConversion>(`/workflow/requirement-candidates/${candidateId}/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}