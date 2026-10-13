import { apiRequest } from './client'

export type Requirement = {
  id: number
  lead_id: number
  title: string
  description: string | null
  required_builtup_area: number | null
  minimum_area: number | null
  maximum_area: number | null
  preferred_state: string | null
  preferred_city: string | null
  preferred_locality: string | null
  radius_km: number | null
  warehouse_type: string | null
  required_clear_height: number | null
  required_docks: number | null
  truck_parking_required: boolean | null
  temperature_controlled: boolean | null
  budget_per_sqft: number | null
  lease_duration_months: number | null
  move_in_timeframe: string | null
  requirement_status: string
  created_at: string
  updated_at: string
}

export type RequirementEvidence = {
  id: number
  requirement_id: number
  source: string
  source_type: string | null
  source_url: string | null
  observed_evidence: string
  inference: string | null
  classification: 'FACT' | 'INFERENCE' | 'UNKNOWN'
  evidence_date: string | null
  verification_status: string
  confidence: number | string | null
  notes: string | null
  verified_at: string | null
  created_at: string
  updated_at: string
}

export type RequirementAssessment = {
  requirement_id: number
  requirement_confidence: number | string | null
  geography_confidence: number | string | null
  size_confidence: number | string | null
  timing_confidence: number | string | null
  operational_confidence: number | string | null
  commercial_confidence: number | string | null
  evidence_strength: number | string | null
  reasons: string[]
  freshness: 'FRESH' | 'AGING' | 'STALE' | 'UNKNOWN'
  freshness_anchor: string | null
  calculated_at: string
}

export type RequirementIntelligence = {
  organization_id: number
  requirement: Requirement
  company_name: string
  evidence: RequirementEvidence[]
  assessment: RequirementAssessment | null
  market_signal_ids: number[]
}

export type WarehouseMatch = {
  id: number
  lead_id: number
  requirement_id: number | null
  warehouse_id: number
  match_score: number
  match_rank: number | null
  geo_distance_km: number | null
  transit_days: number | null
  capacity_fit: number | null
  budget_fit: number | null
  requirement_compatibility: string | null
  match_reasons: string | null
  concern_reasons: string | null
  top_reason: string | null
  status: string
  matched_by: string
  model_id: string | null
  model_version: string | null
  reviewed_by_user_id: number | null
  reviewed_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
  match_level: string
}

export type WarehouseMatchConversion = {
  conversion: { id: number; status: string; warehouse_match_id: number; deal_id: number | null; created_at: string; converted_at: string | null }
  deal: { id: number; deal_name: string; lead_id: number; requirement_id: number; selected_warehouse_match_id: number | null }
  created: boolean
}

export function listRequirementIntelligence(organizationId: number, query = '', status = '') {
  const params = new URLSearchParams({ organization_id: String(organizationId) })
  if (query.trim()) params.set('query', query.trim())
  if (status && status !== 'ALL') params.set('status', status)
  return apiRequest<RequirementIntelligence[]>(`/requirement-intelligence?${params.toString()}`)
}

export function getRequirementIntelligence(id: number) {
  return apiRequest<RequirementIntelligence>(`/requirement-intelligence/${id}`)
}

export function listWarehouseMatches(requirementId: number) {
  return apiRequest<WarehouseMatch[]>(`/warehouse-matches/?requirement_id=${requirementId}`)
}

export function convertWarehouseMatch(matchId: number, payload: { deal_name: string; requirement_id: number; stage_id: number; expected_revenue?: number; currency?: string; notes?: string }) {
  return apiRequest<WarehouseMatchConversion>(`/workflow/warehouse-matches/${matchId}/opportunities`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
