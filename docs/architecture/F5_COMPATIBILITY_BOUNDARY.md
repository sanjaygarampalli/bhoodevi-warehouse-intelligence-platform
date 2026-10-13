# F5 Compatibility Boundary

F5 uses additive, organization-owned tables and does not rewrite the legacy company-intelligence foundation.

| Area | F5 ownership | Existing ownership |
|---|---|---|
| Company identity | normalized name/domain, aliases, source identifiers, lifecycle and duplicate review | `companies` remains the canonical tenant-owned company record |
| Regional presence | `f5_regional_presence` | market signals may continue to describe individual events |
| Claims/evidence | `f5_evidence_claims`, including FACT/INFERENCE/UNKNOWN, freshness and confidence | `market_signal_evidence` remains F4 signal evidence |
| ICP/suitability | `f5_assessments`, explainable dimensions and reasons | legacy ICP/opportunity routes remain backward compatible |
| Requirement | explicitly UNKNOWN in F5 responses | F6 owns confirmed size, timing, commodity, specification and budget |
| People and contact | not owned by F5 | F7/F8 and legacy compatibility models |
| Final lead/opportunity scoring | not owned by F5 | F9+ and legacy opportunity logic |

The F5 API is namespaced under `/f5` to avoid changing existing company routes. A company may be manually created through the legacy company API and then receive an F5 profile. Duplicate indicators are review states only; F5 never automatically merges records.

## Authorization and discovery contract

All F5 records are scoped to the canonical `companies.organization_id`; profile, assessment, presence, and claim queries also require the same organization ID. Global administrators may access an explicitly supplied organization context, consistent with the existing authorization service. F5 list requests reject a global administrator request without `organization_id` rather than silently enumerating tenants. Non-admin users require an active membership, and mutations additionally require an organization write role.

`GET /f5/companies` supports server-side `search`, `industry`, `geography`, `lifecycle_status`, `warehouse_suitability`, `confidence`, `freshness`, `duplicate_status`, `page`, and `page_size` filters. Results are deterministically ordered by company name and ID. Freshness is deterministic: FRESH is at most 90 days old, AGING is 91–365 days, STALE is older, and UNKNOWN has no usable date.

The F5 frontend uses the first active organization returned by `/auth/me` for ordinary organization users. It never puts tokens in URLs and displays API failures distinctly from empty results. Global administrators must use an explicit organization context; a tenant picker is intentionally not inferred from the frontend.