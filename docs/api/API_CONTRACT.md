# BWIP API Contract

## 1. Contract Status

- **Baseline commit:** `1942267715d44e93fc561d506594e84a3791a125` (`fix: install test client dependency in CI`)
- **Alembic head:** `r3d4e5f6a7b8`
- **Test baseline:** 773 passing, 0 failed
- **Baseline date:** 2026-09-15
- **Purpose:** This document and `openapi-baseline.json` freeze the current FastAPI/OpenAPI surface as the backend contract for frontend integration. The machine-readable artifact is generated directly from `app.openapi()`.

## 2. API Principles

- The backend exposes the current API through the v1 route module (`app.api.v1`); the current paths do not add a `/v1` URL prefix.
- Organization membership and ownership checks are enforced by backend dependencies/services where an operation accesses organization-owned data.
- Authentication, authorization, organization isolation, and backend-derived intelligence are backend responsibilities; clients consume the resulting contract.
- Companies and company intelligence are separate from the sales pipeline resources (leads, deals, and follow-up tasks).
- Explicit workflow and outreach operations are exposed as mutating endpoints; no endpoint is documented as autonomous lead, deal, or outreach creation.

## 3. Authentication & Authorization

- **Authentication:** public registration is `POST /auth/register`; login is `POST /auth/login` using OAuth2 password-form fields (`username` and `password`). Successful login returns the bearer token response defined in OpenAPI. Tokens are JWTs with the `sub` claim set to the user email and a 60-minute expiry.
- **Protected endpoints:** except for `/`, `/health`, `/ready`, registration, and login, operations declare the `OAuth2PasswordBearer` security scheme. Send the token as `Authorization: Bearer <token>`.
- **401 behavior:** malformed/invalid tokens, missing token claims, unknown users, inactive users, and invalid login credentials are rejected with 401 by the current implementation.
- **Global administration:** a user with the global `admin` role bypasses organization membership checks and is required by organization-management operations that use `get_current_admin`.
- **Organization isolation:** non-global-admin users need an active membership for the target organization. Organization reads require access; organization writes require a write-capable membership; organization membership administration requires an owner/admin membership. The defined membership roles are `OWNER`, `ADMIN`, `MANAGER`, and `MEMBER`; owner/admin are administration roles and all four are write roles.
- **403 behavior:** access without an active membership, insufficient organization write/administration access, or non-admin access to global-admin operations returns 403. Resource ownership failures are also protected by organization checks.
- **404 behavior:** missing resources and organization-owned resources outside the caller's permitted organization are commonly represented as 404 by endpoint/service handlers; exact operation responses are authoritative in OpenAPI and implementation.
- OpenAPI declares the authentication scheme and operation-level security requirement; detailed organization checks are implemented in dependencies and services and are not fully expressible in the generated schema.

## 4. Endpoint Catalog

Each row below is generated from the current OpenAPI operations. Parameters include path/query values; request body media types and schema references are shown where present. Response codes are the codes declared by OpenAPI. `422` is the standard request-validation response where declared.

### Action Intelligence

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /action-intelligence/actions` | Read Actions | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.priority`, `query.action_type`, `query.limit`, `query.organization_id`; body: ? | `200` (ActionRecommendationListResponse), `422` (HTTPValidationError) | Read-only |
| `GET /action-intelligence/leads/{lead_id}` | Read Lead Actions | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required), `query.limit`, `query.organization_id`; body: ? | `200` (ActionRecommendationListResponse), `422` (HTTPValidationError) | Read-only |
| `GET /action-intelligence/summary` | Read Action Summary | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.organization_id`; body: ? | `200` (ActionIntelligenceSummaryResponse), `422` (HTTPValidationError) | Read-only |
| `GET /action-intelligence/today` | Read Today Actions | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.limit`, `query.organization_id`; body: ? | `200` (ActionRecommendationListResponse), `422` (HTTPValidationError) | Read-only |

### Authentication

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `POST /auth/login` | Login | Public | Not applicable | ?; body: `application/x-www-form-urlencoded`: Body_login_auth_login_post | `200` (Token), `422` (HTTPValidationError) | Mutating |
| `POST /auth/register` | Register | Public | Not applicable | ?; body: `application/json`: UserCreate | `201` (UserResponse), `422` (HTTPValidationError) | Mutating |

### Commercial Intelligence

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /commercial-intelligence/outcomes/summary` | Outcome Summary | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.organization_id` (required), `query.from_date`, `query.to_date`; body: ? | `200` (OutcomeSummary), `422` (HTTPValidationError) | Read-only |

### Companies

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /companies/` | Read All Companies | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: ? | `200` (array of CompanyResponse) | Read-only |
| `POST /companies/` | Create New Company | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: CompanyCreate | `200` (CompanyResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/prospect-priorities` | List Company Prospect Priorities | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.organization_id` (required); body: ? | `200` (CompanyProspectPriorityList), `422` (HTTPValidationError) | Read-only |
| `DELETE /companies/{company_id}` | Delete Existing Company | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}` | Read Company | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (CompanyResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /companies/{company_id}` | Update Existing Company | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: CompanyUpdate | `200` (CompanyResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/prospect-priority` | Read Company Prospect Priority | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (CompanyProspectPriority), `422` (HTTPValidationError) | Read-only |

### Company Intelligence

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /companies/decision-maker-priorities` | Decision Maker Queue | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.organization_id` (required), `query.company_id`, `query.minimum_relevance`, `query.has_email`, `query.has_phone`, `query.has_linkedin`; body: ? | `200` (DecisionMakerQueueResponse), `422` (HTTPValidationError) | Read-only |
| `GET /companies/{company_id}/contact-intelligence` | Contact Intelligence | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (ContactIntelligenceResponse), `422` (HTTPValidationError) | Read-only |
| `GET /companies/{company_id}/contacts` | Contacts | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `query.page`, `query.page_size`, `query.q`, `query.job_title`, `query.department`, `query.seniority`, `query.verification_status`, `query.has_linkedin`; body: ? | `200` (Page), `422` (HTTPValidationError) | Read-only |
| `POST /companies/{company_id}/contacts` | Create Contact | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: ContactWrite | `201` (ContactResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/decision-maker-priorities` | Decision Maker Priorities | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (DecisionMakerCompanyAssessmentResponse), `422` (HTTPValidationError) | Read-only |
| `GET /companies/{company_id}/icp-assessment` | Icp | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (AssessmentResponse), `422` (HTTPValidationError) | Read-only |
| `POST /companies/{company_id}/icp-assessment/recalculate` | Recalculate Icp | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (AssessmentResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/intelligence` | Intelligence | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Read-only |
| `GET /companies/{company_id}/intelligence-profile` | Get Intelligence Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (IntelligenceProfileResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /companies/{company_id}/intelligence-profile` | Update Intelligence Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: IntelligenceProfileUpdate | `200` (IntelligenceProfileResponse), `422` (HTTPValidationError) | Mutating |
| `POST /companies/{company_id}/intelligence-profile` | Create Intelligence Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: IntelligenceProfileWrite | `201` (IntelligenceProfileResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/next-best-action` | Next Action | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (ActionResponse), `422` (HTTPValidationError) | Read-only |
| `POST /companies/{company_id}/next-best-action/recalculate` | Recalculate Next Action | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (ActionResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/opportunity-assessment` | Opportunity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (AssessmentResponse), `422` (HTTPValidationError) | Read-only |
| `POST /companies/{company_id}/opportunity-assessment/recalculate` | Recalculate Opportunity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (AssessmentResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/warehouse-profile` | Get Warehouse Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (WarehouseProfileResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /companies/{company_id}/warehouse-profile` | Update Warehouse Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: WarehouseProfileUpdate | `200` (WarehouseProfileResponse), `422` (HTTPValidationError) | Mutating |
| `POST /companies/{company_id}/warehouse-profile` | Create Warehouse Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: WarehouseProfileWrite | `201` (WarehouseProfileResponse), `422` (HTTPValidationError) | Mutating |
| `GET /company-contact-methods/{method_id}` | Get Method | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.method_id` (required); body: ? | `200` (ContactMethodResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /company-contact-methods/{method_id}` | Update Method | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.method_id` (required); body: `application/json`: ContactMethodUpdate | `200` (ContactMethodResponse), `422` (HTTPValidationError) | Mutating |
| `GET /company-contacts/{contact_id}` | Get Contact | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.contact_id` (required); body: ? | `200` (ContactResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /company-contacts/{contact_id}` | Update Contact | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.contact_id` (required); body: `application/json`: ContactUpdate | `200` (ContactResponse), `422` (HTTPValidationError) | Mutating |
| `POST /company-contacts/{contact_id}/methods` | Create Method | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.contact_id` (required); body: `application/json`: ContactMethodWrite | `201` (ContactMethodResponse), `422` (HTTPValidationError) | Mutating |

### Contact Workflow

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /companies/{company_id}/contact-activity-history` | Company Contact History | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (array of OutreachResponse), `422` (HTTPValidationError) | Read-only |
| `GET /companies/{company_id}/contacts/{contact_id}/investigation` | Read Investigation | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required); body: ? | `200` (Response Read Investigation Companies  Company Id  Contacts  Contact Id  Investigation Get), `422` (HTTPValidationError) | Read-only |
| `PATCH /companies/{company_id}/contacts/{contact_id}/investigation` | Update Investigation | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required); body: `application/json`: InvestigationWrite | `200` (InvestigationResponse), `422` (HTTPValidationError) | Mutating |
| `POST /companies/{company_id}/contacts/{contact_id}/investigation` | Create Investigation | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required); body: `application/json`: InvestigationWrite | `200` (InvestigationResponse), `422` (HTTPValidationError) | Mutating |
| `POST /companies/{company_id}/contacts/{contact_id}/outreach` | Record Outreach | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required); body: `application/json`: OutreachWrite | `200` (OutreachResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/contacts/{contact_id}/outreach-history` | Outreach History | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required); body: ? | `200` (array of OutreachResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /companies/{company_id}/contacts/{contact_id}/outreach/{activity_id}` | Update Outreach | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required), `path.activity_id` (required); body: `application/json`: OutreachUpdate | `200` (OutreachResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/contacts/{contact_id}/pipeline-context` | Pipeline Context | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required); body: ? | `200` (PipelineContext), `422` (HTTPValidationError) | Read-only |
| `POST /companies/{company_id}/contacts/{contact_id}/select-for-outreach` | Select Contact | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required); body: ? | `200` (InvestigationResponse), `422` (HTTPValidationError) | Mutating |

### Core / untagged

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /` | Root | Public | Not applicable | ?; body: ? | `200` (?) | Read-only |
| `GET /health` | Health | Public | Not applicable | ?; body: ? | `200` (?) | Read-only |
| `GET /ready` | Readiness | Public | Not applicable | ?; body: ? | `200` (?) | Read-only |

### Deal Pipeline Stages

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /deal-pipeline-stages/` | List Stages | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.organization_id`, `query.is_active`, `query.skip`, `query.limit`; body: ? | `200` (array of DealPipelineStageResponse), `422` (HTTPValidationError) | Read-only |
| `POST /deal-pipeline-stages/` | Create Stage | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: DealPipelineStageCreate | `200` (DealPipelineStageResponse), `422` (HTTPValidationError) | Mutating |
| `DELETE /deal-pipeline-stages/{stage_id}` | Delete Stage | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.stage_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /deal-pipeline-stages/{stage_id}` | Get Stage | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.stage_id` (required); body: ? | `200` (DealPipelineStageResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /deal-pipeline-stages/{stage_id}` | Update Stage | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.stage_id` (required); body: `application/json`: DealPipelineStageUpdate | `200` (DealPipelineStageResponse), `422` (HTTPValidationError) | Mutating |

### Deals

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /deals/` | List Deals | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.stage_id`, `query.lead_id`, `query.organization_id`, `query.is_active`, `query.skip`, `query.limit`; body: ? | `200` (array of DealResponse), `422` (HTTPValidationError) | Read-only |
| `POST /deals/` | Create Deal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: DealCreate | `200` (DealResponse), `422` (HTTPValidationError) | Mutating |
| `GET /deals/{deal_id}` | Get Deal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: ? | `200` (DealResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /deals/{deal_id}` | Update Deal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: `application/json`: DealUpdate | `200` (DealResponse), `422` (HTTPValidationError) | Mutating |
| `GET /deals/{deal_id}/activities` | List Deal Activities | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: ? | `200` (array of LeadActivityResponse), `422` (HTTPValidationError) | Read-only |
| `POST /deals/{deal_id}/activities` | Create Deal Activity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: `application/json`: DealActivityCreate | `200` (LeadActivityResponse), `422` (HTTPValidationError) | Mutating |
| `GET /deals/{deal_id}/follow-up-tasks` | List Deal Follow Up Tasks | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: ? | `200` (array of FollowUpTaskResponse), `422` (HTTPValidationError) | Read-only |
| `POST /deals/{deal_id}/follow-up-tasks` | Create Deal Follow Up Task | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: `application/json`: DealFollowUpTaskCreate | `200` (FollowUpTaskResponse), `422` (HTTPValidationError) | Mutating |
| `GET /deals/{deal_id}/history` | Get History | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required), `query.skip`, `query.limit`; body: ? | `200` (array of DealStageHistoryResponse), `422` (HTTPValidationError) | Read-only |
| `GET /deals/{deal_id}/opportunity` | Get Opportunity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: ? | `200` (OpportunitySummary), `422` (HTTPValidationError) | Read-only |
| `POST /deals/{deal_id}/transition` | Transition Deal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: `application/json`: DealTransition | `200` (DealResponse), `422` (HTTPValidationError) | Mutating |

### Decision Makers

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `POST /decision-makers/` | Create New Decision Maker | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: DecisionMakerCreate | `200` (DecisionMakerResponse), `422` (HTTPValidationError) | Mutating |
| `GET /decision-makers/company/{company_id}` | Read Decision Makers By Company | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (array of DecisionMakerResponse), `422` (HTTPValidationError) | Read-only |
| `DELETE /decision-makers/{decision_maker_id}` | Delete Existing Decision Maker | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.decision_maker_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /decision-makers/{decision_maker_id}` | Read Decision Maker | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.decision_maker_id` (required); body: ? | `200` (DecisionMakerResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /decision-makers/{decision_maker_id}` | Update Existing Decision Maker | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.decision_maker_id` (required); body: `application/json`: DecisionMakerUpdate | `200` (DecisionMakerResponse), `422` (HTTPValidationError) | Mutating |

### Follow-up Tasks

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /follow-up-tasks/` | List Tasks | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.lead_id`, `query.deal_id`, `query.assigned_to_user_id`, `query.status`, `query.queue`, `query.skip`, `query.limit`; body: ? | `200` (array of FollowUpTaskResponse), `422` (HTTPValidationError) | Read-only |
| `POST /follow-up-tasks/` | Create Task | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: FollowUpTaskCreate | `200` (FollowUpTaskResponse), `422` (HTTPValidationError) | Mutating |
| `GET /follow-up-tasks/{task_id}` | Get Task | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.task_id` (required); body: ? | `200` (FollowUpTaskResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /follow-up-tasks/{task_id}` | Update Task | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.task_id` (required); body: `application/json`: FollowUpTaskUpdate | `200` (FollowUpTaskResponse), `422` (HTTPValidationError) | Mutating |
| `POST /follow-up-tasks/{task_id}/cancel` | Cancel Task | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.task_id` (required); body: `application/json`: TaskCancellation | `200` (FollowUpTaskResponse), `422` (HTTPValidationError) | Mutating |
| `POST /follow-up-tasks/{task_id}/complete` | Complete Task | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.task_id` (required); body: `application/json`: TaskCompletion | `200` (FollowUpTaskResponse), `422` (HTTPValidationError) | Mutating |

### Industries

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /industries/` | Read All Industries | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.skip`, `query.limit`; body: ? | `200` (array of IndustryResponse), `422` (HTTPValidationError) | Read-only |
| `POST /industries/` | Create New Industry | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: IndustryCreate | `200` (IndustryResponse), `422` (HTTPValidationError) | Mutating |
| `GET /industries/code/{code}` | Read Industry By Code | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.code` (required); body: ? | `200` (IndustryResponse), `422` (HTTPValidationError) | Read-only |
| `DELETE /industries/{industry_id}` | Delete Existing Industry | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.industry_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /industries/{industry_id}` | Read Industry | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.industry_id` (required); body: ? | `200` (IndustryResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /industries/{industry_id}` | Update Existing Industry | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.industry_id` (required); body: `application/json`: IndustryUpdate | `200` (IndustryResponse), `422` (HTTPValidationError) | Mutating |

### Lead Activities

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /leads/{lead_id}/activities/` | Read Activities By Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: ? | `200` (array of LeadActivityResponse), `422` (HTTPValidationError) | Read-only |
| `POST /leads/{lead_id}/activities/` | Create New Lead Activity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: `application/json`: LeadActivityCreate | `200` (LeadActivityResponse), `422` (HTTPValidationError) | Mutating |
| `DELETE /leads/{lead_id}/activities/{activity_id}` | Delete Existing Lead Activity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required), `path.activity_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /leads/{lead_id}/activities/{activity_id}` | Read Lead Activity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required), `path.activity_id` (required); body: ? | `200` (LeadActivityResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /leads/{lead_id}/activities/{activity_id}` | Update Existing Lead Activity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required), `path.activity_id` (required); body: `application/json`: LeadActivityUpdate | `200` (LeadActivityResponse), `422` (HTTPValidationError) | Mutating |

### Leads

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `POST /leads/` | Create New Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: LeadCreate | `200` (LeadResponse), `422` (HTTPValidationError) | Mutating |
| `GET /leads/company/{company_id}` | Read Leads By Company | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (array of LeadResponse), `422` (HTTPValidationError) | Read-only |
| `GET /leads/prioritized` | Read Prioritized Leads | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.priority`, `query.minimum_score`, `query.industry`, `query.organization_id`, `query.has_active_requirement`, `query.status`, `query.research_required`, `query.limit`, `query.offset`; body: ? | `200` (PrioritizedLeadResponse), `422` (HTTPValidationError) | Read-only |
| `DELETE /leads/{lead_id}` | Delete Existing Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /leads/{lead_id}` | Read Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: ? | `200` (LeadResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /leads/{lead_id}` | Update Existing Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: `application/json`: LeadUpdate | `200` (LeadResponse), `422` (HTTPValidationError) | Mutating |
| `GET /leads/{lead_id}/intelligence` | Read Lead Intelligence | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: ? | `200` (LeadIntelligenceResponse), `422` (HTTPValidationError) | Read-only |
| `POST /leads/{lead_id}/intelligence/calculate` | Calculate Lead Intelligence | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: ? | `200` (LeadIntelligenceResponse), `422` (HTTPValidationError) | Mutating |
| `GET /leads/{lead_id}/intelligence/history` | Read Lead Intelligence History | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required), `query.limit`, `query.offset`; body: ? | `200` (array of LeadIntelligenceResponse), `422` (HTTPValidationError) | Read-only |
| `POST /leads/{lead_id}/next-action/task` | Create Next Action Task | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: `application/json`: NextActionTaskCreate | `200` (FollowUpTaskResponse), `422` (HTTPValidationError) | Mutating |

### Market Signals

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /market-signals` | List Market Signals | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.organization_id` (required), `query.company_id`, `query.signal_type`, `query.status`, `query.confidence_level`; body: ? | `200` (array of MarketSignalResponse), `422` (HTTPValidationError) | Read-only |
| `POST /market-signals` | Create Market Signal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: MarketSignalCreate | `201` (MarketSignalResponse), `422` (HTTPValidationError) | Mutating |
| `GET /market-signals/{signal_id}` | Get Market Signal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required); body: ? | `200` (MarketSignalResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /market-signals/{signal_id}` | Update Market Signal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required); body: `application/json`: MarketSignalUpdate | `200` (MarketSignalResponse), `422` (HTTPValidationError) | Mutating |
| `GET /market-signals/{signal_id}/assessment` | Assess Market Signal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required); body: ? | `200` (MarketSignalAssessmentResponse), `422` (HTTPValidationError) | Read-only |
| `GET /market-signals/{signal_id}/evidence` | List Signal Evidence | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required); body: ? | `200` (array of MarketSignalEvidenceResponse), `422` (HTTPValidationError) | Read-only |
| `POST /market-signals/{signal_id}/evidence` | Create Signal Evidence | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required); body: `application/json`: MarketSignalEvidenceCreate | `201` (MarketSignalEvidenceResponse), `422` (HTTPValidationError) | Mutating |
| `GET /market-signals/{signal_id}/evidence/{evidence_id}` | Get Signal Evidence | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required), `path.evidence_id` (required); body: ? | `200` (MarketSignalEvidenceResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /market-signals/{signal_id}/evidence/{evidence_id}` | Update Signal Evidence | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required), `path.evidence_id` (required); body: `application/json`: MarketSignalEvidenceUpdate | `200` (MarketSignalEvidenceResponse), `422` (HTTPValidationError) | Mutating |
| `POST /market-signals/{signal_id}/requirement-candidate` | Create Requirement Candidate | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required); body: ? | `201` (RequirementCandidateResponse), `422` (HTTPValidationError) | Mutating |
| `POST /market-signals/{signal_id}/transition` | Transition Market Signal | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.signal_id` (required); body: `application/json`: MarketSignalTransition | `200` (MarketSignalResponse), `422` (HTTPValidationError) | Mutating |

### Operational Intelligence

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /operational-dashboard` | Read Operational Dashboard | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.top_priorities_limit`, `query.recent_activity_limit`, `query.organization_id`; body: ? | `200` (OperationalDashboard), `422` (HTTPValidationError) | Read-only |

### Organization Memberships

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /organizations/{organization_id}/members` | List Members | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required); body: ? | `200` (array of OrganizationMembershipResponse), `422` (HTTPValidationError) | Read-only |
| `POST /organizations/{organization_id}/members` | Create Member | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required); body: `application/json`: OrganizationMembershipCreate | `201` (OrganizationMembershipResponse), `422` (HTTPValidationError) | Mutating |
| `DELETE /organizations/{organization_id}/members/{membership_id}` | Deactivate Member | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required), `path.membership_id` (required); body: ? | `200` (OrganizationMembershipResponse), `422` (HTTPValidationError) | Mutating |
| `GET /organizations/{organization_id}/members/{membership_id}` | Get Member | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required), `path.membership_id` (required); body: ? | `200` (OrganizationMembershipResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /organizations/{organization_id}/members/{membership_id}` | Update Member | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required), `path.membership_id` (required); body: `application/json`: OrganizationMembershipUpdate | `200` (OrganizationMembershipResponse), `422` (HTTPValidationError) | Mutating |

### Organizations

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /organizations/` | Read All Organizations | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.skip`, `query.limit`; body: ? | `200` (array of OrganizationResponse), `422` (HTTPValidationError) | Read-only |
| `POST /organizations/` | Create New Organization | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: OrganizationCreate | `200` (OrganizationResponse), `422` (HTTPValidationError) | Mutating |
| `GET /organizations/code/{org_code}` | Read Organization By Org Code | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.org_code` (required); body: ? | `200` (OrganizationResponse), `422` (HTTPValidationError) | Read-only |
| `GET /organizations/public-id/{public_id}` | Read Organization By Public Id | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.public_id` (required); body: ? | `200` (OrganizationResponse), `422` (HTTPValidationError) | Read-only |
| `DELETE /organizations/{organization_id}` | Delete Existing Organization | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /organizations/{organization_id}` | Read Organization | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required); body: ? | `200` (OrganizationResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /organizations/{organization_id}` | Update Existing Organization | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required); body: `application/json`: OrganizationUpdate | `200` (OrganizationResponse), `422` (HTTPValidationError) | Mutating |

### Prospect Prioritization

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /prospect-prioritization/dashboard` | Read Priority Dashboard | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.organization_id`, `query.top_n`; body: ? | `200` (PriorityDashboardSummary), `422` (HTTPValidationError) | Read-only |
| `GET /prospect-prioritization/leads` | List Priority Leads | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.limit`, `query.offset`, `query.industry`, `query.organization_id`, `query.has_active_requirement`, `query.status`, `query.minimum_priority_score`; body: ? | `200` (LeadPriorityListResponse), `422` (HTTPValidationError) | Read-only |
| `GET /prospect-prioritization/leads/{lead_id}` | Read Priority Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: ? | `200` (LeadPriorityResult), `422` (HTTPValidationError) | Read-only |
| `GET /prospect-prioritization/opportunities` | List Priority Opportunities | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.limit`, `query.offset`, `query.organization_id`, `query.minimum_priority_score`; body: ? | `200` (OpportunityPriorityListResponse), `422` (HTTPValidationError) | Read-only |
| `GET /prospect-prioritization/opportunities/{deal_id}` | Read Priority Opportunity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: ? | `200` (OpportunityPriorityResult), `422` (HTTPValidationError) | Read-only |

### Requirement Candidates

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /requirement-candidates` | List Requirement Candidates | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.organization_id` (required), `query.company_id`, `query.status`, `query.demand_strength`; body: ? | `200` (array of RequirementCandidateResponse), `422` (HTTPValidationError) | Read-only |
| `GET /requirement-candidates/{candidate_id}` | Get Requirement Candidate | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.candidate_id` (required); body: ? | `200` (RequirementCandidateResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /requirement-candidates/{candidate_id}` | Update Requirement Candidate | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.candidate_id` (required); body: `application/json`: RequirementCandidateUpdate | `200` (RequirementCandidateResponse), `422` (HTTPValidationError) | Mutating |
| `POST /requirement-candidates/{candidate_id}/transition` | Transition Requirement Candidate | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.candidate_id` (required); body: `application/json`: RequirementCandidateTransition | `200` (RequirementCandidateResponse), `422` (HTTPValidationError) | Mutating |

### Requirements

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /leads/{lead_id}/requirements/` | Read Requirements By Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: ? | `200` (array of RequirementResponse), `422` (HTTPValidationError) | Read-only |
| `POST /leads/{lead_id}/requirements/` | Create New Requirement | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: `application/json`: RequirementCreate | `200` (RequirementResponse), `422` (HTTPValidationError) | Mutating |
| `DELETE /leads/{lead_id}/requirements/{requirement_id}` | Delete Existing Requirement | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required), `path.requirement_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /leads/{lead_id}/requirements/{requirement_id}` | Read Requirement | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required), `path.requirement_id` (required); body: ? | `200` (RequirementResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /leads/{lead_id}/requirements/{requirement_id}` | Update Existing Requirement | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required), `path.requirement_id` (required); body: `application/json`: RequirementUpdate | `200` (RequirementResponse), `422` (HTTPValidationError) | Mutating |

### Response Qualification

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `POST /companies/intelligence-consolidation` | Consolidate Company | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: CompanyCreate | `200` (?), `422` (HTTPValidationError) | Mutating |
| `POST /companies/intelligence-resolution` | Resolve Company | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: CompanyResolutionRequest | `200` (ResolutionResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/commercial-context` | Commercial Context | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (CommercialContextResponse), `422` (HTTPValidationError) | Read-only |
| `POST /companies/{company_id}/contacts/intelligence-consolidation` | Consolidate Contact | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: ContactResolutionRequest | `200` (?), `422` (HTTPValidationError) | Mutating |
| `POST /companies/{company_id}/contacts/intelligence-resolution` | Resolve Contact | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: ContactResolutionRequest | `200` (ResolutionResponse), `422` (HTTPValidationError) | Mutating |
| `POST /companies/{company_id}/contacts/{contact_id}/outreach/{outreach_id}/qualification` | Create Qualification | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required), `path.outreach_id` (required); body: `application/json`: QualificationWrite | `201` (QualificationResponse), `422` (HTTPValidationError) | Mutating |
| `PATCH /companies/{company_id}/contacts/{contact_id}/outreach/{outreach_id}/qualification/{assessment_id}` | Update Qualification | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required), `path.outreach_id` (required), `path.assessment_id` (required); body: `application/json`: QualificationWrite | `200` (QualificationResponse), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/contacts/{contact_id}/qualifications` | Qualification History | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.contact_id` (required); body: ? | `200` (array of QualificationResponse), `422` (HTTPValidationError) | Read-only |
| `POST /companies/{company_id}/explicit-lead-progression` | Explicit Lead Progression | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: ExplicitLeadProgression | `201` (Response Explicit Lead Progression Companies  Company Id  Explicit Lead Progression Post), `422` (HTTPValidationError) | Mutating |
| `GET /companies/{company_id}/qualifications/{assessment_id}` | Read Qualification | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required), `path.assessment_id` (required); body: ? | `200` (QualificationResponse), `422` (HTTPValidationError) | Read-only |

### Warehouse Capability Matching

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /companies/{company_id}/warehouse-requirement-profile` | Get Requirement Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (RequirementProfileResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /companies/{company_id}/warehouse-requirement-profile` | Update Requirement Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: RequirementProfileWrite | `200` (RequirementProfileResponse), `422` (HTTPValidationError) | Mutating |
| `POST /companies/{company_id}/warehouse-requirement-profile` | Create Requirement Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: RequirementProfileWrite | `201` (RequirementProfileResponse), `422` (HTTPValidationError) | Mutating |
| `POST /warehouse-matches/evaluate` | Evaluate Match | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: WarehouseEvaluationRequest | `200` (WarehouseEvaluationResponse), `422` (HTTPValidationError) | Mutating |
| `GET /warehouses/{warehouse_id}/capability-profile` | Get Capability Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: ? | `200` (CapabilityProfileResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /warehouses/{warehouse_id}/capability-profile` | Update Capability Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: `application/json`: CapabilityProfileWrite | `200` (CapabilityProfileResponse), `422` (HTTPValidationError) | Mutating |
| `POST /warehouses/{warehouse_id}/capability-profile` | Create Capability Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: `application/json`: CapabilityProfileWrite | `201` (CapabilityProfileResponse), `422` (HTTPValidationError) | Mutating |

### Warehouse Matches

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /warehouse-matches/` | Read Warehouse Matches | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `query.lead_id`, `query.warehouse_id`, `query.requirement_id`, `query.limit`, `query.offset`; body: ? | `200` (array of WarehouseMatchResponse), `422` (HTTPValidationError) | Read-only |
| `POST /warehouse-matches/` | Create New Warehouse Match | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: WarehouseMatchCreate | `200` (WarehouseMatchResponse), `422` (HTTPValidationError) | Mutating |
| `POST /warehouse-matches/requirements/{requirement_id}/generate` | Generate Warehouse Matches | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.requirement_id` (required); body: ? | `200` (WarehouseMatchGenerationResponse), `422` (HTTPValidationError) | Mutating |
| `GET /warehouse-matches/requirements/{requirement_id}/recommendations` | Recommend Warehouses | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.requirement_id` (required), `query.limit`; body: ? | `200` (WarehouseMatchRecommendationResponse), `422` (HTTPValidationError) | Read-only |
| `DELETE /warehouse-matches/{match_id}` | Delete Existing Warehouse Match | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.match_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /warehouse-matches/{match_id}` | Read Warehouse Match | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.match_id` (required); body: ? | `200` (WarehouseMatchResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /warehouse-matches/{match_id}` | Update Existing Warehouse Match | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.match_id` (required); body: `application/json`: WarehouseMatchUpdate | `200` (WarehouseMatchResponse), `422` (HTTPValidationError) | Mutating |

### Warehouse Pilot

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /companies/{company_id}/warehouse-requirement-assessment` | Get Requirement Assessment | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: ? | `200` (RequirementAssessmentResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /companies/{company_id}/warehouse-requirement-assessment` | Update Requirement Assessment | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: RequirementAssessmentWrite | `200` (RequirementAssessmentResponse), `422` (HTTPValidationError) | Mutating |
| `POST /companies/{company_id}/warehouse-requirement-assessment` | Create Requirement Assessment | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.company_id` (required); body: `application/json`: RequirementAssessmentWrite | `201` (RequirementAssessmentResponse), `422` (HTTPValidationError) | Mutating |
| `POST /warehouse-pilot-assessments/evaluate` | Evaluate Pilot | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: PilotAssessmentRequest | `200` (PilotAssessmentResponse), `422` (HTTPValidationError) | Mutating |
| `POST /warehouse-pilot-assessments/evaluate-and-persist` | Evaluate And Persist | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: WarehousePilotAssessmentCreateRequest | `201` (WarehousePilotAssessmentResult), `422` (HTTPValidationError) | Mutating |
| `GET /warehouse-pilot-assessments/{assessment_id}` | Get Assessment | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.assessment_id` (required); body: ? | `200` (WarehousePilotAssessmentResponse), `422` (HTTPValidationError) | Read-only |
| `GET /warehouses/{warehouse_id}/commercial-profile` | Get Commercial Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: ? | `200` (CommercialProfileResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /warehouses/{warehouse_id}/commercial-profile` | Update Commercial Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: `application/json`: CommercialProfileWrite | `200` (CommercialProfileResponse), `422` (HTTPValidationError) | Mutating |
| `POST /warehouses/{warehouse_id}/commercial-profile` | Create Commercial Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: `application/json`: CommercialProfileWrite | `201` (CommercialProfileResponse), `422` (HTTPValidationError) | Mutating |
| `GET /warehouses/{warehouse_id}/operational-profile` | Get Operational Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: ? | `200` (OperationalProfileResponse), `422` (HTTPValidationError) | Read-only |
| `PATCH /warehouses/{warehouse_id}/operational-profile` | Update Operational Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: `application/json`: OperationalProfileWrite | `200` (OperationalProfileResponse), `422` (HTTPValidationError) | Mutating |
| `POST /warehouses/{warehouse_id}/operational-profile` | Create Operational Profile | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: `application/json`: OperationalProfileWrite | `201` (OperationalProfileResponse), `422` (HTTPValidationError) | Mutating |

### Warehouses

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `GET /warehouses/` | Read All Warehouses | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: ? | `200` (array of WarehouseResponse) | Read-only |
| `POST /warehouses/` | Create New Warehouse | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | ?; body: `application/json`: WarehouseCreate | `200` (WarehouseResponse), `422` (HTTPValidationError) | Mutating |
| `DELETE /warehouses/{warehouse_id}` | Delete Existing Warehouse | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: ? | `200` (?), `422` (HTTPValidationError) | Mutating |
| `GET /warehouses/{warehouse_id}` | Read Warehouse | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: ? | `200` (WarehouseResponse), `422` (HTTPValidationError) | Read-only |
| `PUT /warehouses/{warehouse_id}` | Update Existing Warehouse | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_id` (required); body: `application/json`: WarehouseUpdate | `200` (WarehouseResponse), `422` (HTTPValidationError) | Mutating |

### Workflow

| Operation | Purpose | Authentication | Organization scope | Request parameters/body | Responses | Mode |
|---|---|---|---|---|---|---|
| `POST /workflow/deals/{deal_id}/transition` | Transition Deal With Lead Advancement | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.deal_id` (required); body: `application/json`: DealTransition | `200` (DealResponse), `422` (HTTPValidationError) | Mutating |
| `POST /workflow/leads/{lead_id}/disqualify` | Disqualify Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: `application/json`: DisqualifyLeadRequest | `200` (QualifyLeadResponse), `422` (HTTPValidationError) | Mutating |
| `POST /workflow/leads/{lead_id}/opportunities` | Create Opportunity | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: `application/json`: CreateOpportunityRequest | `200` (CreateOpportunityResponse), `422` (HTTPValidationError) | Mutating |
| `POST /workflow/leads/{lead_id}/qualify` | Qualify Lead | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: ? | `200` (QualifyLeadResponse), `422` (HTTPValidationError) | Mutating |
| `POST /workflow/leads/{lead_id}/transition` | Transition Lead Status | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.lead_id` (required); body: `application/json`: LeadTransitionRequest | `200` (LeadTransitionResponse), `422` (HTTPValidationError) | Mutating |
| `POST /workflow/organizations/{organization_id}/pipeline/seed` | Seed Default Pipeline | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.organization_id` (required); body: ? | `200` (SeedPipelineResponse), `422` (HTTPValidationError) | Mutating |
| `POST /workflow/requirement-candidates/{candidate_id}/convert` | Convert Requirement Candidate | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.candidate_id` (required); body: `application/json`: RequirementCandidateConversionRequest | `200` (RequirementCandidateConversionResult), `422` (HTTPValidationError) | Mutating |
| `GET /workflow/warehouse-intelligence-conversions/{conversion_id}` | Get Conversion | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.conversion_id` (required); body: ? | `200` (WarehouseIntelligenceConversionResponse), `422` (HTTPValidationError) | Read-only |
| `POST /workflow/warehouse-matches/{warehouse_match_id}/opportunities` | Convert Warehouse Match | Required (OAuth2 bearer) | Backend/service-dependent; see authorization rules above | `path.warehouse_match_id` (required); body: `application/json`: WarehouseMatchOpportunityConversionRequest | `200` (WarehouseMatchOpportunityConversionResponse), `422` (HTTPValidationError) | Mutating |

## 5. Frontend Integration Rules

- Use the current backend API surface and the protected operations' bearer-token flow; do not connect directly to PostgreSQL.
- Treat backend response models and service results as authoritative. Do not reproduce backend business rules in the frontend where the backend already owns them.
- Display backend-derived scores, priorities, assessments, recommendations, and intelligence rather than calculating competing values client-side.
- Preserve organization boundaries in navigation, requests, caching, and displayed data; never use an organization identifier to bypass backend authorization.
- Treat verified contact information and contact intelligence as protected backend data.
- Keep company intelligence distinct from sales pipeline data and workflows.
- Do not create leads, deals, or outreach autonomously; use the explicit backend operations and human-controlled workflow actions.

## 6. Compatibility Policy

Existing v1 endpoints are considered contract-stable.

Future backend changes should:
- prefer additive changes;
- avoid removing or renaming existing fields;
- avoid changing field meaning;
- avoid changing successful response semantics;
- avoid changing status-code semantics without explicit review;
- avoid breaking organization and security guarantees.

New endpoints are allowed in future modules and do **not** constitute a contract regression by themselves. Breaking changes require explicit backend/frontend coordination.

## 7. Baseline Reference

- **Git commit SHA:** `1942267715d44e93fc561d506594e84a3791a125`
- **Alembic head:** `r3d4e5f6a7b8`
- **Test count:** 773 passing
- **Date:** 2026-09-15

### OpenAPI inventory

- **Title:** `BHOODEVI Warehouse Intelligence Platform`
- **Version:** `0.1.0`
- **Paths:** 124
- **HTTP operations:** 185
- **Tags:** none declared globally; endpoint tags are listed in the catalog where supplied by each router.
