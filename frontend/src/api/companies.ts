import { apiRequest } from './client'

export type Company = {
  id: number; organization_id: number; company_name: string; legal_name?: string | null
  industry: string; company_type: string; products?: string | null; website?: string | null
  headquarters_city?: string | null; headquarters_state?: string | null; headquarters_country?: string | null
  business_status?: string | null; priority?: string | null; data_source?: string | null; notes?: string | null
  created_at: string; updated_at: string
}
export type ContactMethod = { id: number; contact_id: number; method_type: string; value: string; verification_status?: string | null }
export type Contact = { id: number; company_id: number; full_name?: string | null; job_title?: string | null; department?: string | null; seniority?: string | null; methods: ContactMethod[] }
export type ContactPage = { items: Contact[]; page: number; page_size: number; total: number }
export type ProspectPriority = { company_id: number; company_name: string; priority: string; priority_score: number; demand_strength: string; evidence_confidence: string; observed_facts: string[]; demand_indicators: string[]; commercial_context: { existing_lead: boolean; existing_requirement: boolean; active_deal: boolean; pipeline_status: string }; inference: string; uncertainties: string[]; recommended_next_action: string; human_review_required: boolean; score_reasons: { points: number; reason: string }[] }
export type DecisionMakerAssessment = { contact: Contact; rank?: number | null; relevance: string; relevance_score: number; reasons: string[]; observed_facts: string[]; inference: string; recommendation: string; uncertainty: string[]; contact_methods: Record<string, boolean>; contactability_status: string; company_prospect_priority: string; company_prospect_score: number; human_review_required: boolean }
export type DecisionMakerAssessmentResponse = { company_id: number; company_name: string; prospect_priority: Record<string, unknown>; commercial_context: Record<string, unknown>; contacts: DecisionMakerAssessment[]; total: number; human_review_required: boolean }
export type CommercialContext = { company_id: number; active_lead_ids: number[]; active_requirement_ids: number[]; active_deal_ids: number[]; qualification_ids: number[]; context: string; recommended_next_action: string; human_review_required: boolean }
export type IntelligenceProfile = { industry?: string | null; sub_industry?: string | null; business_model?: string | null; headquarters_city?: string | null; headquarters_state?: string | null; headquarters_country?: string | null; operational_geography?: Record<string, unknown> | null; is_expanding: boolean; is_hiring: boolean; is_entering_new_market: boolean; is_raising_capacity: boolean; is_launching_new_product: boolean; is_opening_new_facility: boolean; indicator_evidence?: Record<string, unknown> | null }
export type Activity = { id: number; contact_id: number; method: string; performed_at: string; purpose?: string | null; summary?: string | null; outcome?: string | null; response_status?: string | null; next_action?: string | null }

export type F5Profile = { id: number; organization_id: number; company_id: number; normalized_name: string; normalized_domain?: string | null; registration_identifier?: string | null; source_identifier?: string | null; aliases: string[]; lifecycle_status: string; duplicate_status: string; source?: string | null; last_verified_at?: string | null; created_at: string; updated_at: string }
export type F5Assessment = { id: number; organization_id: number; company_id: number; industry_classification: string; industry?: string | null; warehouse_suitability: string; icp_classification: string; dimensions: Record<string, unknown>; reasons: string[]; confidence?: number | null; confidence_reasons: string[]; evidence_count: number; freshness: string; calculated_at: string }
export type F5Presence = { id: number; profile_id: number; presence_type: string; region: string; city?: string | null; district?: string | null; state?: string | null; country?: string | null; classification: string; confidence?: number | null; observed_at?: string | null; last_verified_at?: string | null; freshness: string; source?: string | null; source_url?: string | null; notes?: string | null }
export type F5Evidence = { id: number; profile_id: number; claim: string; claim_type: string; classification: string; source?: string | null; source_url?: string | null; source_title?: string | null; published_at?: string | null; observed_at?: string | null; last_verified_at?: string | null; freshness: string; credibility?: string | null; confidence?: number | null; confidence_reasons: string[]; created_at: string }
export type F5Company = { id: number; organization_id: number; company_name: string; legal_name?: string | null; industry: string; company_type: string; website?: string | null; headquarters_city?: string | null; headquarters_state?: string | null; profile: F5Profile | null; assessment: F5Assessment | null }
export type F5CompanyDetail = F5Company & { presence: F5Presence[]; evidence: F5Evidence[]; current_warehouse_requirement: { value: null; classification: 'UNKNOWN' } }
export type F5CompanyPage = { items: F5Company[]; page: number; page_size: number; total: number }

export function listCompanies() { return apiRequest<Company[]>('/companies/') }
export function getCompany(id: number) { return apiRequest<Company>(`/companies/${id}`) }
export function getPriority(id: number) { return apiRequest<ProspectPriority>(`/companies/${id}/prospect-priority`) }
export function getContacts(id: number) { return apiRequest<ContactPage>(`/companies/${id}/contacts`) }
export function getDecisionMakers(id: number) { return apiRequest<DecisionMakerAssessmentResponse>(`/companies/${id}/decision-maker-priorities`) }
export function getCommercialContext(id: number) { return apiRequest<CommercialContext>(`/companies/${id}/commercial-context`) }
export function getIntelligenceProfile(id: number) { return apiRequest<IntelligenceProfile>(`/companies/${id}/intelligence-profile`) }
export function getActivity(id: number) { return apiRequest<Activity[]>(`/companies/${id}/contact-activity-history`) }
export function listF5Companies(params: { organizationId: number; page?: number; pageSize?: number; search?: string; industry?: string; geography?: string; suitability?: string; lifecycleStatus?: string; confidence?: string; freshness?: string; duplicateStatus?: string } ) {
  const query = new URLSearchParams({ organization_id: String(params.organizationId), page: String(params.page ?? 1), page_size: String(params.pageSize ?? 25) })
  const values: Record<string, string | undefined> = { search: params.search, industry: params.industry, geography: params.geography, warehouse_suitability: params.suitability, lifecycle_status: params.lifecycleStatus, confidence: params.confidence, freshness: params.freshness, duplicate_status: params.duplicateStatus }
  Object.entries(values).forEach(([key, value]) => { if (value) query.set(key, value) })
  return apiRequest<F5CompanyPage>(`/f5/companies?${query.toString()}`)
}
export function getF5Company(id: number) { return apiRequest<F5CompanyDetail>(`/f5/companies/${id}`) }
