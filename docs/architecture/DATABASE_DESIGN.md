# Database Architecture — BHOODEVI Warehouse Intelligence Platform (BWIP)

**Document:** Complete Database Design (Next Generation)

**Version:** 2.0.0 (Revised — Requirement Domain added in §5.3)

**Status:** Approved Design (Updated: Requirement entity, Lead Activity & Warehouse Match relationships)

**Last Updated:** August 2026

**Database Technology:** PostgreSQL 15+ (Primary), Redis (Cache Layer — future), Elasticsearch (Search — future)

---

## 1. Introduction

BWIP is an **AI-powered Warehouse Business Development Platform**. It is **not** a Warehouse Management System and **not** an Inventory Management System.

The database is the foundation for:

- Discovering and researching companies that require warehouse space.
- Profiling decision makers who control warehouse leasing decisions.
- Capturing structured warehouse requirements per lead — the primary input for the AI warehouse matching engine.
- Detecting opportunity signals (news, hiring, factory expansion, import/export activity).
- Scoring, matching, and recommending leads and warehouses using AI.
- Executing outreach across Email, LinkedIn, and WhatsApp.
- Managing follow-up tasks and the deal pipeline.
- Continuously learning from AI recommendations, feedback, and outcomes.

This document defines every table, its columns, data types, keys, foreign keys, relationships, indexes, and constraints. It concludes with entity relationships, normalization analysis, scalability, and performance strategy.

---

## 2. Design Conventions

These conventions apply to every table unless stated otherwise.

### 2.1 Identifiers

- Every table has a surrogate primary key `id BIGINT GENERATED ALWAYS AS IDENTITY`.
- Core externally-exposed entities (organizations, users, companies, warehouses, decision_makers, leads, requirements, deals, campaigns) also carry `public_id UUID` with a unique index. Public IDs are used in URLs/APIs; numeric IDs are used internally to avoid enumeration.
- Provider-managed message identifiers (Email, LinkedIn, WhatsApp, AI models) are stored with unique constraints.

### 2.2 Temporal Columns

- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` (maintained by application)

### 2.3 Audit Columns

- `created_by_user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL`
- `updated_by_user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL`
- Nullable because system/AI processes create rows with no human actor.

### 2.4 Soft Delete

- `is_deleted BOOLEAN NOT NULL DEFAULT FALSE` on master data tables (companies, warehouses, decision_makers, leads, requirements, campaigns).
- Queries filter `WHERE is_deleted = FALSE`; a partial index is defined per table to keep the index small.

### 2.5 Tenant Isolation

- Every business table carries `organization_id BIGINT NOT NULL REFERENCES organizations(id)`.
- `organizations` are the tenant (the warehouse owner / leasing company using BWIP).
- Global lookup tables (`industries`) do not carry `organization_id`.
- Multi-tenancy is enforced by Row-Level Security (RLS) policies on `organization_id` in production.

### 2.6 Enumerations

- Bounded values are stored as `VARCHAR` with `CHECK` constraints, not native PostgreSQL ENUM types. This avoids painful migration locking and keeps validation at the application layer.

### 2.7 Flexible Payloads

- `JSONB` is used for genuinely variable, AI-produced, or sparse data (score factors, campaign criteria, provider metadata, token usage).
- JSONB is **not** used to model attributes that are queried relationally.

### 2.8 Money & Quantities

- Money: `NUMERIC(14,2)` plus `currency CHAR(3)` (ISO 4217, default `'INR'`).
- Areas: `NUMERIC(14,2)` square feet.
- Percentages / scores: `NUMERIC(5,2)` with `CHECK (x >= 0 AND x <= 100)`.

### 2.9 Index Naming

- `uq_table__column` — unique constraint
- `ix_table__column` — single-column index
- `ix_table__col1__col2` — composite index

### 2.10 Delete Rules (default policy)

- `RESTRICT` for critical business dependencies (leads, companies, deals).
- `SET NULL` for audit/user references.
- `CASCADE` only for pure child detail tables (signal subtype tables, stage history).

---

## 3. Foundation Tables

### 3.1 `organizations`

**Purpose:** Represents a tenant — a warehouse owner, leasing company, or 3PL that uses BWIP to acquire long-term leasing clients.

**Primary Key:** `id`

**Foreign Keys:** `industry_id → industries(id)`

**Relationships:**

- 1—N with `users`, `warehouses`, `companies`, `leads`, `deals`, `outreach_campaigns`, `follow_up_tasks`.
- N—1 with `industries`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| org_code | VARCHAR(20) | No | Short unique tenant code |
| legal_name | VARCHAR(255) | No | Registered legal entity name |
| trading_name | VARCHAR(255) | Yes | Display / brand name |
| org_type | VARCHAR(50) | No | CHECK: SOLE_PROPRIETOR, PARTNERSHIP, LLP, PVT_LTD, PUBLIC_LTD, GOVT, OTHER |
| industry_id | BIGINT | Yes | Primary industry of the tenant |
| gstin | VARCHAR(15) | Yes | GST identification number |
| pan | VARCHAR(10) | Yes | PAN number |
| website | VARCHAR(255) | Yes | Website URL |
| email | VARCHAR(255) | Yes | Primary contact email |
| phone | VARCHAR(30) | Yes | Primary contact phone |
| address_line1 | VARCHAR(255) | Yes | Street address |
| address_line2 | VARCHAR(255) | Yes | Detail / landmark |
| city | VARCHAR(100) | Yes | City |
| state | VARCHAR(100) | Yes | State / province |
| country | VARCHAR(100) | No | Default 'India' |
| postal_code | VARCHAR(20) | Yes | PIN / ZIP |
| subscription_tier | VARCHAR(20) | No | CHECK: FREE, STARTER, GROWTH, ENTERPRISE |
| status | VARCHAR(20) | No | CHECK: TRIAL, ACTIVE, SUSPENDED, CANCELLED |
| settings | JSONB | Yes | Feature flags, defaults, integrations config |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `uq_organizations__public_id` unique
- `uq_organizations__org_code` unique
- `uq_organizations__gstin` unique (partial — where not null)
- `uq_organizations__pan` unique (partial — where not null)
- `ix_organizations__city`

**Constraints:**

- `CHECK (email IS NULL OR email LIKE '%@%')`
- `CHECK (status IN ('TRIAL','ACTIVE','SUSPENDED','CANCELLED'))`
- `CHECK (org_type IN ('SOLE_PROPRIETOR','PARTNERSHIP','LLP','PVT_LTD','PUBLIC_LTD','GOVT','OTHER'))`

---

### 3.2 `users`

**Purpose:** Stores platform users (business development managers, analysts, admins) belonging to an organization.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `created_by_user_id → users(id)`

**Relationships:**

- N—1 with `organizations`.
- 1—N with `leads` (owner), `lead_activities`, `outreach_campaigns` (owner), `ai_recommendations` (acted_by), `follow_up_tasks` (assigned/created).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| organization_id | BIGINT | No | Owning tenant |
| full_name | VARCHAR(255) | No | Display name |
| email | VARCHAR(255) | No | Login email (lowercased) |
| phone | VARCHAR(30) | Yes | Contact number |
| password_hash | VARCHAR(255) | No | Argon2/bcrypt hash |
| role | VARCHAR(30) | No | CHECK: ORG_ADMIN, BD_MANAGER, BD_EXECUTIVE, ANALYST, VIEWER, SUPER_ADMIN |
| designation | VARCHAR(100) | Yes | Job title inside tenant |
| is_active | BOOLEAN | No | Account enabled |
| email_verified | BOOLEAN | No | Email verified |
| last_login_at | TIMESTAMPTZ | Yes | Most recent login |
| preferences | JSONB | Yes | UI / notification preferences |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Created by (admin) |

**Indexes:**

- `uq_users__organization__email` unique on `(organization_id, lower(email))`
- `uq_users__public_id` unique
- `ix_users__role`

**Constraints:**

- `CHECK (role IN ('ORG_ADMIN','BD_MANAGER','BD_EXECUTIVE','ANALYST','VIEWER','SUPER_ADMIN'))`
- `CHECK (is_active IN (TRUE, FALSE))`

---

### 3.3 `industries`

**Purpose:** Global lookup of industry classifications (NIC-based) to normalize company and tenant data and enable industry-level analytics.

**Primary Key:** `id`

**Foreign Keys:** None.

**Relationships:**

- 1—N with `companies`, `organizations`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| code | VARCHAR(20) | No | Industry code (NIC / custom) |
| name | VARCHAR(100) | No | Industry name |
| category | VARCHAR(100) | Yes | High-level sector (Manufacturing, Retail, FMCG…) |
| description | TEXT | Yes | Description |
| is_active | BOOLEAN | No | Available for selection |

**Indexes:**

- `uq_industries__code` unique
- `uq_industries__name` unique
- `ix_industries__category`

---

## 4. Company & Warehouse Domain

### 4.1 `companies`

**Purpose:** Stores **prospect / target companies** researched by BWIP — organizations that may need warehouse space. (Distinct from `organizations`, which are BWIP tenants.)

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `industry_id → industries(id)`, `created_by_user_id/updated_by_user_id → users(id)`

**Relationships:**

- N—1 with `organizations` (tenant research ownership).
- N—1 with `industries`.
- 1—N with `company_locations`, `decision_makers`, `leads`, `opportunity_signals`, `deals`, `emails`, `linkedin_messages`, `whatsapp_messages`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| organization_id | BIGINT | No | Researching tenant |
| company_name | VARCHAR(255) | No | Display name |
| legal_name | VARCHAR(255) | Yes | Registered name |
| domain | VARCHAR(255) | Yes | Company website domain (dedup key) |
| industry_id | BIGINT | Yes | Industry lookup |
| company_type | VARCHAR(50) | No | CHECK: PRIVATE, PUBLIC, GOVT, PSU, MNC, STARTUP, OTHER |
| description | TEXT | Yes | Business description |
| website | VARCHAR(255) | Yes | Website |
| hq_city | VARCHAR(100) | Yes | Headquarters city |
| hq_state | VARCHAR(100) | Yes | Headquarters state |
| hq_country | VARCHAR(100) | No | Default 'India' |
| hq_pincode | VARCHAR(20) | Yes | Headquarters PIN |
| employee_count_range | VARCHAR(30) | Yes | e.g. '501-1000' |
| annual_revenue | NUMERIC(14,2) | Yes | Estimated annual revenue |
| currency | CHAR(3) | Yes | Default 'INR' |
| founded_year | SMALLINT | Yes | Year founded |
| phone | VARCHAR(30) | Yes | Main phone |
| linkedin_url | VARCHAR(255) | Yes | LinkedIn company page |
| data_source | VARCHAR(100) | Yes | Where discovered (Tavily, Serper, manual…) |
| external_id | VARCHAR(255) | Yes | Source-system company ID |
| entity_status | VARCHAR(20) | No | CHECK: ACTIVE, INACTIVE, DORMANT, BANKRUPT, ACQUIRED |
| enrichment_score | NUMERIC(5,2) | Yes | Data completeness 0–100 |
| data_quality_notes | JSONB | Yes | Missing fields & confidence flags |
| is_deleted | BOOLEAN | No | Soft delete flag |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |
| updated_by_user_id | BIGINT | Yes | Last modifying user |

**Indexes:**

- `uq_companies__organization__public_id` unique
- `uq_companies__organization__domain` unique partial `WHERE domain IS NOT NULL AND is_deleted = FALSE`
- `ix_companies__company_name` (btree)
- `ix_companies__company_name_trgm` GIN trigram for fuzzy name search
- `ix_companies__industry_id`
- `ix_companies__hq_city`
- `ix_companies__is_deleted` partial `WHERE is_deleted = FALSE`

**Constraints:**

- `CHECK (company_type IN ('PRIVATE','PUBLIC','GOVT','PSU','MNC','STARTUP','OTHER'))`
- `CHECK (enrichment_score IS NULL OR (enrichment_score >= 0 AND enrichment_score <= 100))`

---

### 4.2 `company_locations`

**Purpose:** Stores all physical locations of a prospect company (HQ, factories, distribution centers, regional offices). Enables geo-aware warehouse matching and signal correlation.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `company_id → companies(id) ON DELETE CASCADE`, audit user FKs.

**Relationships:**

- N—1 with `companies`.
- 1—N with `opportunity_signals` (optional location link, via JSON/columns in signal subtype tables).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| company_id | BIGINT | No | Parent company |
| location_type | VARCHAR(30) | No | CHECK: HEADQUARTERS, REGIONAL_OFFICE, FACTORY, DISTRIBUTION_CENTER, WAREHOUSE, BRANCH, OTHER |
| location_name | VARCHAR(255) | Yes | e.g. 'Chennai Plant' |
| address_line1 | VARCHAR(255) | Yes | Street address |
| address_line2 | VARCHAR(255) | Yes | Detail |
| city | VARCHAR(100) | Yes | City |
| state | VARCHAR(100) | Yes | State |
| country | VARCHAR(100) | No | Default 'India' |
| postal_code | VARCHAR(20) | Yes | PIN |
| latitude | NUMERIC(9,6) | Yes | Latitude |
| longitude | NUMERIC(9,6) | Yes | Longitude |
| is_primary | BOOLEAN | No | Is headquarters / primary |
| is_active | BOOLEAN | No | Location still valid |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |

**Indexes:**

- `ix_company_locations__company_id`
- `ix_company_locations__company_id__is_primary` partial
- `ix_company_locations__lat__lng` (for PostGIS GiST upgrade)

**Constraints:**

- `CHECK (location_type IN ('HEADQUARTERS','REGIONAL_OFFICE','FACTORY','DISTRIBUTION_CENTER','WAREHOUSE','BRANCH','OTHER'))`
- `CHECK (latitude IS NULL OR (latitude BETWEEN -90 AND 90))`
- `CHECK (longitude IS NULL OR (longitude BETWEEN -180 AND 180))`
- At most one `is_primary = TRUE` per company (application or partial unique index on `(company_id) WHERE is_primary = TRUE`).

---

### 4.3 `warehouses`

**Purpose:** Stores the warehouse assets of the tenant (warehouse owner). These are the supply side of BWIP — matched against lead requirements and recommended in AI matches.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, audit user FKs.

**Relationships:**

- N—1 with `organizations`.
- 1—N with `warehouse_matches`, `deals` (selected warehouse).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| organization_id | BIGINT | No | Owning tenant |
| warehouse_name | VARCHAR(255) | No | Display name |
| warehouse_code | VARCHAR(30) | No | Internal code |
| warehouse_type | VARCHAR(30) | No | CHECK: COVERED, OPEN_YARD, COLD_STORAGE, BONDED, MULTIPURPOSE, CONTAINER, TRANSIT, OTHER |
| total_area_sqft | NUMERIC(14,2) | No | Total area sq ft |
| built_up_area_sqft | NUMERIC(14,2) | Yes | Covered built-up area |
| open_area_sqft | NUMERIC(14,2) | Yes | Open yard area |
| height_ft | NUMERIC(8,2) | Yes | Clear height |
| floor_load_kg_sqm | NUMERIC(10,2) | Yes | Floor load capacity |
| address_line1 | VARCHAR(255) | Yes | Street address |
| address_line2 | VARCHAR(255) | Yes | Detail |
| city | VARCHAR(100) | No | City |
| state | VARCHAR(100) | No | State |
| country | VARCHAR(100) | No | Default 'India' |
| postal_code | VARCHAR(20) | Yes | PIN |
| latitude | NUMERIC(9,6) | No | Latitude |
| longitude | NUMERIC(9,6) | No | Longitude |
| rent_per_month | NUMERIC(14,2) | No | Monthly rent |
| currency | CHAR(3) | No | Default 'INR' |
| min_lease_months | SMALLINT | Yes | Minimum lease term |
| available_from | DATE | Yes | Availability date |
| availability_status | VARCHAR(20) | No | CHECK: AVAILABLE, PARTIAL, OCCUPIED, UNDER_MAINTENANCE, INACTIVE |
| amenities | JSONB | Yes | Power backup, fire safety, CCTV, ramp, parking… |
| certifications | JSONB | Yes | ISO, BIS, CE… |
| condition_grade | CHAR(1) | Yes | CHECK: A, B, C, D |
| occupancy_rate | NUMERIC(5,2) | Yes | Current occupancy % |
| is_deleted | BOOLEAN | No | Soft delete flag |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |
| updated_by_user_id | BIGINT | Yes | Last modifying user |

**Indexes:**

- `uq_warehouses__organization__code` unique
- `uq_warehouses__public_id` unique
- `ix_warehouses__organization__city__status` composite
- `ix_warehouses__type`
- `ix_warehouses__rent_per_month`
- `ix_warehouses__lat__lng` (for PostGIS GiST)
- `ix_warehouses__is_deleted` partial

**Constraints:**

- `CHECK (warehouse_type IN ('COVERED','OPEN_YARD','COLD_STORAGE','BONDED','MULTIPURPOSE','CONTAINER','TRANSIT','OTHER'))`
- `CHECK (availability_status IN ('AVAILABLE','PARTIAL','OCCUPIED','UNDER_MAINTENANCE','INACTIVE'))`
- `CHECK (total_area_sqft > 0)`

---

### 4.4 `decision_makers`

**Purpose:** Stores contacts and key decision makers at prospect companies who influence or approve warehouse leasing decisions.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `company_id → companies(id)`, audit user FKs.

**Relationships:**

- N—1 with `companies`.
- 1—N with `campaign_members`, `emails`, `linkedin_messages`, `whatsapp_messages`, `follow_up_tasks`.
- 1—N with `leads` (as primary decision maker).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| organization_id | BIGINT | No | Owning tenant |
| company_id | BIGINT | No | Parent company |
| full_name | VARCHAR(255) | No | Contact name |
| job_title | VARCHAR(150) | Yes | Current designation |
| department | VARCHAR(100) | Yes | Department |
| seniority | VARCHAR(30) | Yes | CHECK: C_SUITE, VP, DIRECTOR, MANAGER, EXECUTIVE, OTHER |
| role_in_procurement | VARCHAR(30) | Yes | CHECK: FINAL_APPROVER, INFLUENCER, CHAMPION, RECOMMENDER, BLOCKER, UNKNOWN |
| email | VARCHAR(255) | Yes | Work email |
| phone | VARCHAR(30) | Yes | Work phone |
| linkedin_url | VARCHAR(255) | Yes | LinkedIn profile URL |
| location_city | VARCHAR(100) | Yes | City |
| country | VARCHAR(100) | Yes | Default 'India' |
| verification_status | VARCHAR(20) | No | CHECK: UNVERIFIED, PENDING, CROSS_VERIFIED, VERIFIED, INVALID |
| verification_source | VARCHAR(100) | Yes | Tool used / method |
| is_primary_contact | BOOLEAN | No | Default contact for company |
| last_contacted_at | TIMESTAMPTZ | Yes | Last outreach time |
| notes | TEXT | Yes | Free-form notes |
| is_deleted | BOOLEAN | No | Soft delete flag |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |
| updated_by_user_id | BIGINT | Yes | Last modifying user |

**Indexes:**

- `uq_decision_makers__company__email` unique partial `WHERE email IS NOT NULL AND is_deleted = FALSE`
- `uq_decision_makers__company__linkedin` unique partial `WHERE linkedin_url IS NOT NULL AND is_deleted = FALSE`
- `ix_decision_makers__company_id__is_primary` partial
- `ix_decision_makers__verification_status`
- `ix_decision_makers__email`

**Constraints:**

- `CHECK (seniority IN ('C_SUITE','VP','DIRECTOR','MANAGER','EXECUTIVE','OTHER'))`
- `CHECK (verification_status IN ('UNVERIFIED','PENDING','CROSS_VERIFIED','VERIFIED','INVALID'))`
- `CHECK (email IS NOT NULL OR phone IS NOT NULL OR linkedin_url IS NOT NULL)` — at least one channel.

---

## 5. Lead & Opportunity Domain

### 5.1 `leads`

**Purpose:** Represents a business opportunity — a company (or company-location) with one or more warehouse requirements (see §5.3 `requirements`) that BWIP tracks, nurtures, and converts.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `company_id → companies(id)`, `owner_user_id → users(id)`, `primary_decision_maker_id → decision_makers(id)`, `latest_score_snapshot_id → lead_score_snapshots(id)`, audit user FKs.

**Relationships:**

- N—1 with `companies`.
- N—1 with `users` (owner).
- 1—N with `requirements`, `lead_activities`, `lead_score_snapshots`, `warehouse_matches`, `ai_recommendations`, `opportunity_signals`, `follow_up_tasks`, `deals`, `emails`, `linkedin_messages`, `whatsapp_messages`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| organization_id | BIGINT | No | Owning tenant |
| lead_number | VARCHAR(30) | No | Human-readable lead reference |
| company_id | BIGINT | No | Prospect company |
| status | VARCHAR(30) | No | CHECK: NEW, DISCOVERED, CONTACTED, QUALIFIED, POSITIONED, NEGOTIATING, WON, LOST, DISQUALIFIED, DORMANT |
| lead_source | VARCHAR(30) | No | CHECK: AI_DISCOVERY, COMPANY_RESEARCH, SIGNAL_TRIGGER, MANUAL, REFERRAL, INBOUND, TENDER, BROKER, OTHER |
| space_needed_sqft | NUMERIC(14,2) | Yes | Required area |
| warehouse_type | VARCHAR(30) | Yes | Preferred type (mirrors warehouses.warehouse_type) |
| preferred_cities | JSONB | Yes | Array of preferred cities |
| budget_per_month | NUMERIC(14,2) | Yes | Monthly budget |
| currency | CHAR(3) | Yes | Default 'INR' |
| move_in_timeframe | VARCHAR(20) | Yes | CHECK: IMMEDIATE, 1_3_MONTHS, 3_6_MONTHS, 6_12_MONTHS, FLEXIBLE |
| lease_tenure_years | SMALLINT | Yes | Intended lease duration |
| owner_user_id | BIGINT | Yes | Assigned BD user |
| primary_decision_maker_id | BIGINT | Yes | Main contact |
| ai_score | NUMERIC(5,2) | Yes | Denormalized latest total score (0–100) |
| latest_score_snapshot_id | BIGINT | Yes | Pointer to current score snapshot |
| priority | VARCHAR(10) | No | CHECK: LOW, MEDIUM, HIGH, URGENT |
| last_activity_at | TIMESTAMPTZ | Yes | Denormalized last activity time |
| next_follow_up_at | TIMESTAMPTZ | Yes | Next scheduled action |
| disqualified_reason | VARCHAR(150) | Yes | Why disqualified |
| closed_reason | VARCHAR(150) | Yes | Why won/lost (if closed) |
| is_deleted | BOOLEAN | No | Soft delete flag |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |
| updated_by_user_id | BIGINT | Yes | Last modifying user |

**Indexes:**

- `uq_leads__organization__lead_number` unique
- `uq_leads__public_id` unique
- `ix_leads__company_id`
- `ix_leads__status__owner_user_id`
- `ix_leads__ai_score` (descending)
- `ix_leads__next_follow_up_at`
- `ix_leads__created_at`
- `ix_leads__is_deleted` partial

**Constraints:**

- `CHECK (status IN ('NEW','DISCOVERED','CONTACTED','QUALIFIED','POSITIONED','NEGOTIATING','WON','LOST','DISQUALIFIED','DORMANT'))`
- `CHECK (lead_source IN ('AI_DISCOVERY','COMPANY_RESEARCH','SIGNAL_TRIGGER','MANUAL','REFERRAL','INBOUND','TENDER','BROKER','OTHER'))`
- `CHECK (ai_score IS NULL OR (ai_score >= 0 AND ai_score <= 100))`
- `CHECK (move_in_timeframe IN ('IMMEDIATE','1_3_MONTHS','3_6_MONTHS','6_12_MONTHS','FLEXIBLE'))`

> **Requirement-domain note:** the lead-level columns above (`space_needed_sqft`, `warehouse_type`, `preferred_cities`, `budget_per_month`, `move_in_timeframe`, `lease_tenure_years`) are retained as **summary fields** for lead-list dashboards and backward compatibility. The canonical, structured warehouse requirement for a lead now lives in `requirements` (§5.3). New integrations must write requirement detail to `requirements`; the lead-level fields are denormalized from it (see §11.5).

---

### 5.2 `lead_activities`

**Purpose:** Unified timeline of every interaction and event on a lead: calls, emails, LinkedIn messages, WhatsApp messages, meetings, notes, AI actions, and system events.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `lead_id → leads(id)`, `requirement_id → requirements(id)` (optional), `user_id → users(id)`, `related_activity_id` (self, via source reference), audit user FKs.

**Relationships:**

- N—1 with `leads`.
- N—1 with `requirements` (optional — activity context for a specific requirement).
- N—1 with `users` (actor).
- Optional 1—1 with message tables (`emails`, `linkedin_messages`, `whatsapp_messages`) via `activity_source_type` + `activity_source_id`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| lead_id | BIGINT | No | Parent lead |
| requirement_id | BIGINT | Yes | Optional linked requirement |
| activity_type | VARCHAR(30) | No | CHECK: CALL, EMAIL, LINKEDIN, WHATSAPP, MEETING, NOTE, TASK, SYSTEM_EVENT, AI_ACTION, SIGNAL, PROPOSAL, OTHER |
| channel | VARCHAR(20) | Yes | EMAIL, LINKEDIN, WHATSAPP, PHONE, FACE_TO_FACE, SYSTEM |
| subject | VARCHAR(255) | Yes | Short subject |
| summary | TEXT | Yes | Summary text |
| notes | TEXT | Yes | Detailed notes |
| occurred_at | TIMESTAMPTZ | No | When the activity happened |
| duration_minutes | SMALLINT | Yes | Call/meeting duration |
| outcome | VARCHAR(30) | Yes | CHECK: COMPLETED, NO_ANSWER, LEFT_VOICEMAIL, INTERESTED, NOT_INTERESTED, CALLBACK_SCHEDULED, BOUNCED, FAILED, OTHER |
| activity_source_type | VARCHAR(20) | Yes | EMAIL, LINKEDIN, WHATSAPP, TASK, SYSTEM |
| activity_source_id | BIGINT | Yes | Row id in source table |
| user_id | BIGINT | Yes | Actor (null for system/AI) |
| is_deleted | BOOLEAN | No | Soft delete |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `ix_lead_activities__lead_id__occurred_at` (descending)
- `ix_lead_activities__requirement_id`
- `ix_lead_activities__activity_type__occurred_at`
- `ix_lead_activities__activity_source_type__activity_source_id` unique where not null
- `ix_lead_activities__user_id`
- Covering index for timeline: `(lead_id, occurred_at DESC) INCLUDE (activity_type, subject, summary, outcome)`

**Constraints:**

- `CHECK (activity_type IN ('CALL','EMAIL','LINKEDIN','WHATSAPP','MEETING','NOTE','TASK','SYSTEM_EVENT','AI_ACTION','SIGNAL','PROPOSAL','OTHER'))`
- `CHECK (occurred_at >= created_at - INTERVAL '1 day')` (soft sanity check)

---

### 5.3 `requirements`

**Purpose:** Represents a single warehouse requirement received from a client for a lead (business opportunity). A lead may carry multiple requirements — e.g., multiple cities, expansion phases, or product categories. The `requirements` table is the **primary input for the AI Warehouse Matching Engine** and the canonical source of structured warehouse-demand detail.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `lead_id → leads(id) ON DELETE CASCADE`, `created_by_user_id/updated_by_user_id → users(id)`.

**Relationships:**

- N—1 with `leads` (parent opportunity).
- N—1 with `organizations` (tenant).
- 1—N with `warehouse_matches` (match results at requirement granularity).
- 1—N with `lead_activities` (optional per-requirement activity context).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| organization_id | BIGINT | No | Owning tenant |
| lead_id | BIGINT | No | Parent lead |
| title | VARCHAR(255) | No | Short requirement title |
| description | TEXT | Yes | Free-form requirement detail |
| industry | VARCHAR(150) | Yes | Client industry (mirrors `industries.name`) |
| goods_type | VARCHAR(150) | Yes | Goods to be stored |
| storage_type | VARCHAR(30) | Yes | CHECK: AMBIENT, TEMPERATURE_CONTROLLED, CHILLER, FREEZER, HAZMAT, BONDED, OPEN_YARD, AGRICULTURAL, OTHER |
| compliance_requirements | TEXT | Yes | Licenses/certifications needed (FSSAI, ISO, hazmat…) |
| required_builtup_area | NUMERIC(14,2) | Yes | Required covered built-up area (sq ft) |
| required_open_area | NUMERIC(14,2) | Yes | Required open yard area (sq ft) |
| minimum_area | NUMERIC(14,2) | Yes | Minimum acceptable area (sq ft) |
| maximum_area | NUMERIC(14,2) | Yes | Maximum acceptable area (sq ft) |
| preferred_state | VARCHAR(100) | Yes | Preferred state |
| preferred_city | VARCHAR(100) | Yes | Preferred city |
| preferred_locality | VARCHAR(150) | Yes | Preferred locality/industrial zone |
| preferred_pincode | VARCHAR(20) | Yes | Preferred PIN code |
| latitude | NUMERIC(9,6) | Yes | Preferred site latitude |
| longitude | NUMERIC(9,6) | Yes | Preferred site longitude |
| radius_km | NUMERIC(10,2) | Yes | Acceptable radius around preferred location |
| budget_per_sqft | NUMERIC(14,2) | Yes | Budget per sq ft (INR) |
| lease_duration_months | SMALLINT | Yes | Desired lease term (months) |
| security_deposit_months | SMALLINT | Yes | Acceptable security deposit (months) |
| preferred_lease_type | VARCHAR(30) | Yes | CHECK: LEASE, LEAVE_AND_LICENSE, RENTAL, BUILD_TO_SUIT, REVENUE_SHARE, OTHER |
| escalation_percentage | NUMERIC(5,2) | Yes | Acceptable annual escalation % |
| warehouse_type | VARCHAR(30) | Yes | CHECK: COVERED, OPEN_YARD, COLD_STORAGE, BONDED, MULTIPURPOSE, CONTAINER, TRANSIT, OTHER |
| loading_bays_required | SMALLINT | Yes | Number of loading bays |
| dock_level_required | BOOLEAN | No | Dock-level loading required |
| ground_level_required | BOOLEAN | No | Ground-level loading required |
| office_required | BOOLEAN | No | Office space required |
| labour_required | BOOLEAN | No | Labour/manpower required |
| required_clear_height | NUMERIC(8,2) | Yes | Required clear height (ft) |
| required_floor_load | NUMERIC(10,2) | Yes | Required floor load (kg/sqm) |
| required_power_load | NUMERIC(10,2) | Yes | Required power load (kVA) |
| required_docks | SMALLINT | Yes | Number of docks |
| truck_parking_required | BOOLEAN | No | Truck parking required |
| rail_connectivity_required | BOOLEAN | No | Rail siding required |
| fire_noc_required | BOOLEAN | No | Fire NOC required |
| temperature_controlled | BOOLEAN | No | Temperature-controlled facility required |
| operating_hours | VARCHAR(50) | Yes | Desired operating hours (e.g. "24x7", "10:00-22:00") |
| expected_monthly_dispatch | NUMERIC(16,2) | Yes | Expected monthly dispatch volume |
| expected_monthly_receipts | NUMERIC(16,2) | Yes | Expected monthly receipt volume |
| move_in_timeframe | VARCHAR(20) | Yes | CHECK: IMMEDIATE, 1_3_MONTHS, 3_6_MONTHS, 6_12_MONTHS, FLEXIBLE |
| requirement_status | VARCHAR(20) | No | CHECK: DRAFT, ACTIVE, ON_HOLD, CLOSED, CANCELLED |
| ai_match_score | NUMERIC(5,2) | Yes | AI warehouse-match fit 0–100 (model generated) |
| requirement_score | NUMERIC(5,2) | Yes | AI requirement quality/completeness 0–100 (model generated) |
| priority_score | NUMERIC(5,2) | Yes | AI priority/urgency 0–100 (model generated) |
| confidence_score | NUMERIC(5,2) | Yes | AI confidence 0–100 (model generated) |
| is_deleted | BOOLEAN | No | Soft delete flag |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user (null = AI/system) |
| updated_by_user_id | BIGINT | Yes | Last modifying user |

**Indexes:**

- `uq_requirements__public_id` unique
- `ix_requirements__lead_id`
- `ix_requirements__organization_id__requirement_status`
- `ix_requirements__organization_id__requirement_status__priority_score` composite (workspace + AI prioritization)
- `ix_requirements__preferred_state__preferred_city`
- `ix_requirements__ai_match_score` (descending)
- `ix_requirements__lat__lng` (for PostGIS GiST upgrade)
- `ix_requirements__is_deleted` partial `WHERE is_deleted = FALSE`

**Constraints:**

- `CHECK (warehouse_type IN ('COVERED','OPEN_YARD','COLD_STORAGE','BONDED','MULTIPURPOSE','CONTAINER','TRANSIT','OTHER'))`
- `CHECK (move_in_timeframe IN ('IMMEDIATE','1_3_MONTHS','3_6_MONTHS','6_12_MONTHS','FLEXIBLE'))`
- `CHECK (requirement_status IN ('DRAFT','ACTIVE','ON_HOLD','CLOSED','CANCELLED'))`
- `CHECK (preferred_lease_type IN ('LEASE','LEAVE_AND_LICENSE','RENTAL','BUILD_TO_SUIT','REVENUE_SHARE','OTHER'))`
- `CHECK (storage_type IN ('AMBIENT','TEMPERATURE_CONTROLLED','CHILLER','FREEZER','HAZMAT','BONDED','OPEN_YARD','AGRICULTURAL','OTHER'))`
- `CHECK (latitude IS NULL OR (latitude BETWEEN -90 AND 90))`
- `CHECK (longitude IS NULL OR (longitude BETWEEN -180 AND 180))`
- `CHECK (minimum_area IS NULL OR maximum_area IS NULL OR minimum_area <= maximum_area)`
- `CHECK (ai_match_score IS NULL OR (ai_match_score >= 0 AND ai_match_score <= 100))` (same range constraint applies to `requirement_score`, `priority_score`, `confidence_score`)

**Future AI Usage:**

- `requirements` is the source of truth consumed by the **AI Warehouse Matching Engine** (see [AI_AGENTS.md](./AI_AGENTS.md)): every match candidate is scored against a specific requirement row.
- `ai_match_score` stores the engine's top match fit for the requirement; `priority_score` ranks requirements across the lead/opportunity workspace so BD teams focus on the highest-impact needs.
- `requirement_score` and `confidence_score` feed model explainability, thresholding (e.g., auto-route only matches above a confidence floor), and evaluation datasets via `warehouse_matches` outcomes.
- Score columns are **model-generated placeholders** — no AI logic runs in the application layer; the matching/scoring agents write these fields when they execute.

---

### 5.4 `opportunity_signals` (Base / Supertype Table)

**Purpose:** Supertype table for all detected business signals that imply warehouse demand. Concrete signal detail rows (news, hiring, factory expansion, import/export) extend this table via 1:1 foreign keys (Class Table Inheritance).

This table stores common signal metadata: source, timing, relevance, AI intent, deduplication, and disposition.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `company_id → companies(id)`, `lead_id → leads(id)`, `assigned_to_user_id → users(id)`, audit user FKs.

**Relationships:**

- N—1 with `companies`.
- N—1 with `leads` (if the signal created/touched a lead).
- 1—1 with `company_news`, `hiring_signals`, `factory_expansion_signals`, `import_export_signals` (one subtype row per signal).
- 1—N with `lead_activities` (as generated events).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| company_id | BIGINT | No | Company the signal concerns |
| lead_id | BIGINT | Yes | Lead created/linked by this signal |
| signal_type | VARCHAR(30) | No | CHECK: COMPANY_NEWS, HIRING, FACTORY_EXPANSION, IMPORT_EXPORT, TENDER, MARKET_EXPANSION, RELOCATION, OTHER |
| title | VARCHAR(255) | No | Short human title |
| summary | TEXT | Yes | AI-generated summary |
| source_name | VARCHAR(150) | Yes | e.g. Economic Times, LinkedIn, DGFT |
| source_url | VARCHAR(500) | Yes | Original URL |
| source_article_date | DATE | Yes | Date of source content |
| detected_at | TIMESTAMPTZ | No | When AI detected it |
| first_seen_at | TIMESTAMPTZ | No | First appearance |
| last_seen_at | TIMESTAMPTZ | No | Most recent appearance |
| relevance_score | NUMERIC(5,2) | Yes | Relevance to warehouse demand 0–100 |
| confidence | NUMERIC(5,2) | Yes | Detection confidence 0–100 |
| warehouse_intent_code | VARCHAR(10) | Yes | CHECK: HIGH, MEDIUM, LOW, NONE |
| status | VARCHAR(20) | No | CHECK: NEW, REVIEWED, ACTING, ACTED, IGNORED, DUPLICATE, EXPIRED |
| assigned_to_user_id | BIGINT | Yes | BD owner |
| dedup_hash | CHAR(64) | No | SHA-256 of normalized payload |
| findings | JSONB | Yes | Raw AI-parsed payload |
| notes | TEXT | Yes | Manual notes |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user (null = AI) |
| updated_by_user_id | BIGINT | Yes | Last modifying user |

**Indexes:**

- `uq_opportunity_signals__dedup_hash` unique
- `ix_opportunity_signals__company_id__detected_at` (descending)
- `ix_opportunity_signals__signal_type__status`
- `ix_opportunity_signals__lead_id`
- `ix_opportunity_signals__assigned_to_user_id__status`

**Constraints:**

- `CHECK (signal_type IN ('COMPANY_NEWS','HIRING','FACTORY_EXPANSION','IMPORT_EXPORT','TENDER','MARKET_EXPANSION','RELOCATION','OTHER'))`
- `CHECK (status IN ('NEW','REVIEWED','ACTING','ACTED','IGNORED','DUPLICATE','EXPIRED'))`
- `CHECK (warehouse_intent_code IN ('HIGH','MEDIUM','LOW','NONE'))`

---

### 5.5 `company_news` (Signal Subtype)

**Purpose:** Concrete details for signals of type `COMPANY_NEWS` — news about expansion, investment, strategy, partnerships, or restructuring that implies warehouse demand.

**Primary Key:** `id`

**Foreign Keys:** `signal_id → opportunity_signals(id) ON DELETE CASCADE` (UNIQUE), audit user FKs.

**Relationships:**

- 1—1 with `opportunity_signals`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| signal_id | BIGINT | No | Parent signal (unique) |
| headline | VARCHAR(500) | No | News headline |
| article_url | VARCHAR(500) | Yes | Article link |
| publisher | VARCHAR(150) | Yes | Publishing outlet |
| published_at | DATE | Yes | Publish date |
| sentiment | VARCHAR(10) | Yes | CHECK: POSITIVE, NEUTRAL, NEGATIVE |
| sentiment_score | NUMERIC(5,2) | Yes | Sentiment strength 0–100 |
| key_entities | JSONB | Yes | Mentioned companies, people, places |
| summary_extract | TEXT | Yes | AI summary |
| is_trending | BOOLEAN | No | Marked trending |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `uq_company_news__signal_id` unique
- `ix_company_news__published_at`
- GIN on `key_entities`

---

### 5.6 `hiring_signals` (Signal Subtype)

**Purpose:** Concrete details for signals of type `HIRING` — job postings in logistics, operations, supply-chain, procurement, or plant roles that suggest operational growth and warehouse need.

**Primary Key:** `id`

**Foreign Keys:** `signal_id → opportunity_signals(id) ON DELETE CASCADE` (UNIQUE), audit user FKs.

**Relationships:**

- 1—1 with `opportunity_signals`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| signal_id | BIGINT | No | Parent signal (unique) |
| job_title | VARCHAR(255) | No | Job posting title |
| department | VARCHAR(120) | Yes | Department |
| role_function | VARCHAR(120) | Yes | e.g. SUPPLY_CHAIN, OPERATIONS, PROCUREMENT |
| location_city | VARCHAR(100) | Yes | Job location |
| country | VARCHAR(100) | Yes | Job country |
| employment_type | VARCHAR(30) | Yes | FULL_TIME, CONTRACT, INTERNSHIP |
| seniority | VARCHAR(30) | Yes | e.g. MANAGER, LEAD, EXECUTIVE |
| posting_url | VARCHAR(500) | Yes | Job URL |
| posted_at | DATE | Yes | Posting date |
| application_deadline | DATE | Yes | Deadline |
| team_size_hint | VARCHAR(120) | Yes | Team context from JD |
| hiring_volume | SMALLINT | Yes | Number of openings |
| warehouse_relevant | BOOLEAN | No | AI flag: role implies warehouse/logistics need |
| salary_range | VARCHAR(100) | Yes | Stated range |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `uq_hiring_signals__signal_id` unique
- `ix_hiring_signals__posted_at`
- `ix_hiring_signals__warehouse_relevant`

---

### 5.7 `factory_expansion_signals` (Signal Subtype)

**Purpose:** Concrete details for signals of type `FACTORY_EXPANSION` — new plants, facility expansions, relocations, or closures that change warehouse demand.

**Primary Key:** `id`

**Foreign Keys:** `signal_id → opportunity_signals(id) ON DELETE CASCADE` (UNIQUE), audit user FKs.

**Relationships:**

- 1—1 with `opportunity_signals`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| signal_id | BIGINT | No | Parent signal (unique) |
| expansion_type | VARCHAR(30) | No | CHECK: NEW_FACILITY, PLANT_EXPANSION, RELOCATION, NEW_PLANT, CLOSURE, OTHER |
| facility_name | VARCHAR(255) | Yes | Facility / project name |
| location_city | VARCHAR(100) | Yes | City |
| state | VARCHAR(100) | Yes | State |
| country | VARCHAR(100) | Yes | Country |
| announced_at | DATE | Yes | Announcement date |
| ground_break_date | DATE | Yes | Construction start |
| expected_operational_date | DATE | Yes | Go-live date |
| investment_amount | NUMERIC(16,2) | Yes | Investment value |
| currency | CHAR(3) | Yes | Default 'INR' |
| new_area_sqft | NUMERIC(14,2) | Yes | Facility area |
| expected_workforce | SMALLINT | Yes | Headcount at facility |
| project_status | VARCHAR(30) | Yes | CHECK: ANNOUNCED, UNDER_CONSTRUCTION, OPERATIONAL, CANCELLED, COMPLETED |
| project_url | VARCHAR(500) | Yes | Source link |
| approval_details | TEXT | Yes | Approvals / incentives |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `uq_factory_expansion_signals__signal_id` unique
- `ix_factory_expansion_signals__project_status`
- `ix_factory_expansion_signals__expected_operational_date`

---

### 5.8 `import_export_signals` (Signal Subtype)

**Purpose:** Concrete details for signals of type `IMPORT_EXPORT` — trade activity, new licenses, shipment volumes, and logistics tenders that indicate warehousing, cross-docking, or bonded-storage demand.

**Primary Key:** `id`

**Foreign Keys:** `signal_id → opportunity_signals(id) ON DELETE CASCADE` (UNIQUE), audit user FKs.

**Relationships:**

- 1—1 with `opportunity_signals`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| signal_id | BIGINT | No | Parent signal (unique) |
| trade_direction | VARCHAR(10) | No | CHECK: IMPORT, EXPORT, BOTH |
| commodity | VARCHAR(255) | Yes | Traded goods |
| hs_code | VARCHAR(20) | Yes | HS classification |
| origin_city | VARCHAR(100) | Yes | Origin city |
| origin_country | VARCHAR(100) | Yes | Origin country |
| destination_city | VARCHAR(100) | Yes | Destination city |
| destination_country | VARCHAR(100) | Yes | Destination country |
| loading_port | VARCHAR(150) | Yes | Loading port |
| discharge_port | VARCHAR(150) | Yes | Discharge port |
| volume | NUMERIC(16,2) | Yes | Volume/quantity |
| volume_unit | VARCHAR(20) | Yes | TEU, TONNES, KG, UNITS |
| declared_value | NUMERIC(16,2) | Yes | Value of goods |
| currency | CHAR(3) | Yes | Default 'INR' |
| frequency | VARCHAR(20) | Yes | ONE_TIME, RECURRING, SEASONAL |
| license_registration | VARCHAR(255) | Yes | IEC / license details |
| incoterm | VARCHAR(20) | Yes | FOB, CIF, EXW, DDP, OTHER |
| expected_logistics_partner | VARCHAR(150) | Yes | Named 3PL/logistics partner |
| needs_warehousing | BOOLEAN | No | AI flag: warehousing required |
| notes | TEXT | Yes | Additional context |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `uq_import_export_signals__signal_id` unique
- `ix_import_export_signals__trade_direction`
- `ix_import_export_signals__loading_port__discharge_port`

---

## 6. Intelligence Domain

### 6.1 `lead_score_snapshots`

**Purpose:** Stores every lead-scoring evaluation as an immutable snapshot: dimensional scores, AI reasoning, model version, and recommended action. Enables score history, explainability, and model benchmarking.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `lead_id → leads(id)`, `created_by_user_id → users(id)`.

**Relationships:**

- N—1 with `leads`.
- Referenced by `leads.latest_score_snapshot_id`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| lead_id | BIGINT | No | Scored lead |
| score_version | SMALLINT | No | Scoring schema version |
| scored_at | TIMESTAMPTZ | No | Evaluation time |
| total_score | NUMERIC(5,2) | No | Composite 0–100 |
| fit_score | NUMERIC(5,2) | Yes | Company-warehouse fit 0–100 |
| intent_score | NUMERIC(5,2) | Yes | Buying intent 0–100 |
| timing_score | NUMERIC(5,2) | Yes | Urgency/timing 0–100 |
| engagement_score | NUMERIC(5,2) | Yes | Engagement level 0–100 |
| financial_score | NUMERIC(5,2) | Yes | Budget/financial strength 0–100 |
| signal_alignment_score | NUMERIC(5,2) | Yes | Signal strength/correlation 0–100 |
| score_factors | JSONB | No | Per-dimension breakdown, weights, AI reasoning |
| risk_indicators | JSONB | Yes | Budget mismatch, distance, low intent… |
| scoring_method | VARCHAR(30) | No | RULE_BASED, ML_MODEL, HYBRID |
| model_id | VARCHAR(100) | Yes | Model registry id |
| model_version | VARCHAR(50) | Yes | Model version tag |
| recommended_priority | VARCHAR(10) | Yes | LOW, MEDIUM, HIGH, URGENT |
| recommended_next_action | TEXT | Yes | AI suggested next step |
| next_review_at | DATE | Yes | When score should be refreshed |
| created_by_user_id | BIGINT | Yes | Triggering user (null = scheduled AI) |
| created_at | TIMESTAMPTZ | No | Creation timestamp |

**Indexes:**

- `ix_lead_score_snapshots__lead_id__scored_at` (descending)
- `ix_lead_score_snapshots__total_score` (descending)
- `ix_lead_score_snapshots__scored_at__lead_id` (for aggregates)
- `ix_lead_score_snapshots__model_id__score_version`

**Constraints:**

- `CHECK (total_score >= 0 AND total_score <= 100)`
- `CHECK (fit_score >= 0 AND fit_score <= 100)` (same for all dimension scores)
- `CHECK (scoring_method IN ('RULE_BASED','ML_MODEL','HYBRID'))`

---

### 6.2 `warehouse_matches`

**Purpose:** Stores AI-generated and human-curated matches between a lead's warehouse requirement and a specific warehouse, including match score, ranking, geo distance, fit reasons, and disposition. Each match is scoped to a specific `requirements` row (§5.3); matches created before the requirements model existed carry only the legacy lead-level requirement fields (`requirement_id` NULL).

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `lead_id → leads(id)`, `requirement_id → requirements(id)` (optional), `warehouse_id → warehouses(id)`, `reviewed_by_user_id → users(id)`, audit user FKs.

**Relationships:**

- N—1 with `leads` (context opportunity).
- N—1 with `requirements` (matched requirement — canonical demand target).
- N—1 with `warehouses` (candidate).
- Referenced by `deals` when a match becomes a deal.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| lead_id | BIGINT | No | Parent lead (context) |
| requirement_id | BIGINT | Yes | Matched requirement (canonical demand record) |
| warehouse_id | BIGINT | No | Warehouse candidate |
| match_score | NUMERIC(5,2) | No | Composite 0–100 |
| match_rank | SMALLINT | Yes | Rank within lead set |
| geo_distance_km | NUMERIC(10,2) | Yes | Distance lead-location to warehouse |
| transit_days | SMALLINT | Yes | Estimated transit days |
| capacity_fit | NUMERIC(5,2) | Yes | Area compatibility 0–100 |
| budget_fit | NUMERIC(5,2) | Yes | Rent compatibility 0–100 |
| requirement_compatibility | JSONB | Yes | Per-attribute matching detail |
| match_reasons | JSONB | Yes | AI list of supporting reasons |
| concern_reasons | JSONB | Yes | AI list of concerns |
| top_reason | TEXT | Yes | Primary selling point |
| status | VARCHAR(30) | No | CHECK: AI_RECOMMENDED, SHORTLISTED, PROPOSED, LEAD_CHOSEN, REJECTED, CONVERTED, STALE |
| matched_by | VARCHAR(20) | No | AI, MANUAL, HYBRID |
| model_id | VARCHAR(100) | Yes | Matching model id |
| model_version | VARCHAR(50) | Yes | Matching model version |
| reviewed_by_user_id | BIGINT | Yes | Reviewing user |
| reviewed_at | TIMESTAMPTZ | Yes | Review time |
| notes | TEXT | Yes | Notes |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `uq_warehouse_matches__requirement__warehouse` unique partial on `(requirement_id, warehouse_id) WHERE requirement_id IS NOT NULL`
- `uq_warehouse_matches__lead__warehouse` unique partial on `(lead_id, warehouse_id) WHERE requirement_id IS NULL` (legacy lead-level matches)
- `ix_warehouse_matches__requirement_id__match_score` (descending)
- `ix_warehouse_matches__lead_id__match_score` (descending)
- `ix_warehouse_matches__warehouse_id__status`
- `ix_warehouse_matches__status`

**Constraints:**

- `CHECK (match_score >= 0 AND match_score <= 100)`
- `CHECK (status IN ('AI_RECOMMENDED','SHORTLISTED','PROPOSED','LEAD_CHOSEN','REJECTED','CONVERTED','STALE'))`
- `CHECK (matched_by IN ('AI','MANUAL','HYBRID'))`

---

### 6.3 `ai_recommendations`

**Purpose:** Stores every actionable recommendation produced by BWIP AI agents: next best actions, warehouse suggestions, email/LinkedIn/WhatsApp drafts, follow-up reminders, pitch themes, price suggestions, lead prioritization, and signal alerts.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `lead_id → leads(id)`, `company_id → companies(id)`, `acted_by_user_id → users(id)`, audit user FKs.

**Relationships:**

- N—1 with `leads`, `companies`.
- Polymorphic reference to `related_entity_type` + `related_entity_id` (LEAD, COMPANY, DEAL, WAREHOUSE, DECISION_MAKER, SIGNAL, CAMPAIGN, NONE).
- Optional 1—N with `ai_learning_history` (outcome references).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| recommendation_type | VARCHAR(40) | No | CHECK: NEXT_BEST_ACTION, NEW_COMPANY_TARGET, WAREHOUSE_SUGGESTION, EMAIL_DRAFT, LINKEDIN_DRAFT, WHATSAPP_DRAFT, FOLLOWUP_REMINDER, PITCH_THEME, PRICE_SUGGESTION, LEAD_PRIORITIZATION, SIGNAL_ALERT, MARKET_INSIGHT, TEMPLATE, OTHER |
| title | VARCHAR(255) | No | Recommendation title |
| description | TEXT | No | Explanation |
| rationale | TEXT | Yes | Why recommended |
| suggested_action | VARCHAR(255) | Yes | Concrete next step |
| related_entity_type | VARCHAR(30) | No | CHECK: LEAD, COMPANY, DEAL, WAREHOUSE, DECISION_MAKER, SIGNAL, CAMPAIGN, NONE |
| related_entity_id | BIGINT | Yes | Row id of related entity |
| lead_id | BIGINT | Yes | Parent lead (if applicable) |
| company_id | BIGINT | Yes | Parent company (if applicable) |
| confidence_score | NUMERIC(5,2) | No | 0–100 |
| status | VARCHAR(30) | No | CHECK: SUGGESTED, ACCEPTED, DISMISSED, SCHEDULED, EXECUTED, EXPIRED, SUPERSEDED |
| recommendation_payload | JSONB | Yes | Structured agent output (draft body, params…) |
| source_agent | VARCHAR(100) | No | Agent name |
| model_id | VARCHAR(100) | Yes | Model used |
| model_version | VARCHAR(50) | Yes | Model version |
| generated_at | TIMESTAMPTZ | No | Generation time |
| acted_at | TIMESTAMPTZ | Yes | Action time |
| acted_by_user_id | BIGINT | Yes | Acting user |
| feedback | VARCHAR(10) | No | CHECK: THUMBS_UP, THUMBS_DOWN, NOT_RATED (default NOT_RATED) |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `ix_ai_recommendations__status__organization_id`
- `ix_ai_recommendations__related_entity_type__related_entity_id`
- `ix_ai_recommendations__lead_id`
- `ix_ai_recommendations__generated_at`
- `ix_ai_recommendations__source_agent`

**Constraints:**

- `CHECK (status IN ('SUGGESTED','ACCEPTED','DISMISSED','SCHEDULED','EXECUTED','EXPIRED','SUPERSEDED'))`
- `CHECK (feedback IN ('THUMBS_UP','THUMBS_DOWN','NOT_RATED'))`
- `CHECK ((related_entity_id IS NULL) OR (related_entity_id IS NOT NULL AND related_entity_type <> 'NONE'))`

---

### 6.4 `ai_learning_history`

**Purpose:** Immutable audit and learning log of every AI call: agent, model, input, output, latency, tokens, cost, outcome, feedback, and ground truth. This is the training-data and evaluation corpus that powers continuous improvement.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)` (nullable — platform-level calls), `user_id → users(id)` (nullable), audit user FKs.

**Relationships:**

- Optional N—1 with `users`, `organizations`.
- Optional correlation to `ai_recommendations` outcomes via `outcome_reference` JSONB.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | Yes | Tenant (null = platform) |
| user_id | BIGINT | Yes | Requesting user (null = scheduled agent) |
| agent_name | VARCHAR(100) | No | Agent (e.g. signal_scanner, lead_scorer) |
| interface_name | VARCHAR(100) | Yes | Agent entry point / task |
| model_provider | VARCHAR(50) | Yes | OpenAI, Gemini, Claude, local… |
| model_id | VARCHAR(100) | Yes | Model identifier |
| model_version | VARCHAR(50) | Yes | Version tag |
| input_hash | CHAR(64) | No | SHA-256 of normalized input |
| input_context | JSONB | Yes | Structured input snapshot |
| output_payload | JSONB | Yes | Structured output |
| output_summary | TEXT | Yes | Human-readable output |
| confidence | NUMERIC(5,2) | Yes | Model confidence 0–100 |
| latency_ms | INTEGER | Yes | Execution time |
| token_usage | JSONB | Yes | Prompt/completion tokens |
| estimated_cost | NUMERIC(10,4) | Yes | Estimated cost |
| execution_status | VARCHAR(20) | No | CHECK: SUCCESS, PARTIAL, FAILED, CANCELLED |
| user_feedback | VARCHAR(10) | No | CHECK: POSITIVE, NEGATIVE, NEUTRAL, NOT_RATED |
| reward_signal | NUMERIC(5,2) | Yes | Delayed reward (-100..+100) |
| ground_truth | JSONB | Yes | Verified outcome for evaluation |
| outcome_reference | JSONB | Yes | e.g. recommendation accepted, lead converted |
| is_finetuning_candidate | BOOLEAN | No | Flagged for training corpus |
| occurred_at | TIMESTAMPTZ | No | Execution time |
| created_at | TIMESTAMPTZ | No | Insert timestamp |

**Indexes:**

- `ix_ai_learning_history__agent_name__occurred_at` (descending)
- `ix_ai_learning_history__execution_status`
- `ix_ai_learning_history__occurred_at`
- `ix_ai_learning_history__is_finetuning_candidate`
- `ix_ai_learning_history__model_id`
- `uq_ai_learning_history__input_hash` unique partial `WHERE agent_name = 'signal_scanner'` (dedup for high-frequency scans)

**Constraints:**

- `CHECK (execution_status IN ('SUCCESS','PARTIAL','FAILED','CANCELLED'))`
- `CHECK (user_feedback IN ('POSITIVE','NEGATIVE','NEUTRAL','NOT_RATED'))`

---

## 7. Engagement Domain (Outreach)

### 7.1 `outreach_campaigns`

**Purpose:** Groups outreach messages (Email, LinkedIn, WhatsApp) into organized campaigns targeting selected leads/decision makers with sequence logic, templates, and performance stats.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `owner_user_id → users(id)`, audit user FKs.

**Relationships:**

- N—1 with `organizations`, `users` (owner).
- 1—N with `campaign_members`, `emails`, `linkedin_messages`, `whatsapp_messages`, `deals` (source campaign).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| organization_id | BIGINT | No | Owning tenant |
| campaign_name | VARCHAR(255) | No | Campaign title |
| campaign_type | VARCHAR(30) | No | CHECK: COLD_EMAIL, LINKEDIN, WHATSAPP, MULTI_CHANNEL, NURTURE, REACTIVATION |
| goal | TEXT | Yes | Campaign objective |
| status | VARCHAR(20) | No | CHECK: DRAFT, SCHEDULED, ACTIVE, PAUSED, COMPLETED, CANCELLED, ARCHIVED |
| start_at | TIMESTAMPTZ | Yes | Scheduled start |
| end_at | TIMESTAMPTZ | Yes | Scheduled end |
| timezone | VARCHAR(50) | Yes | Sending timezone |
| segment_criteria | JSONB | Yes | Lead/company filter criteria snapshot |
| default_templates | JSONB | Yes | Per-channel template payloads |
| channel_settings | JSONB | Yes | Sending limits, throttling, daily caps |
| total_members | INTEGER | No | Denormalized member count |
| sent_count | INTEGER | No | Denormalized sent count |
| open_count | INTEGER | No | Denormalized open count |
| reply_count | INTEGER | No | Denormalized reply count |
| bounce_count | INTEGER | No | Denormalized bounce/undelivered count |
| total_budget | NUMERIC(14,2) | Yes | Campaign budget |
| currency | CHAR(3) | Yes | Default 'INR' |
| owner_user_id | BIGINT | No | Campaign owner |
| is_deleted | BOOLEAN | No | Soft delete |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |

**Indexes:**

- `uq_outreach_campaigns__public_id` unique
- `ix_outreach_campaigns__organization_id__status`
- `ix_outreach_campaigns__start_at`

**Constraints:**

- `CHECK (campaign_type IN ('COLD_EMAIL','LINKEDIN','WHATSAPP','MULTI_CHANNEL','NURTURE','REACTIVATION'))`
- `CHECK (status IN ('DRAFT','SCHEDULED','ACTIVE','PAUSED','COMPLETED','CANCELLED','ARCHIVED'))`

---

### 7.2 `campaign_members`

**Purpose:** Resolves the many-to-many relationship between campaigns and decision makers/leads, and tracks per-member sequencing, personalization, and send/reply status.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `campaign_id → outreach_campaigns(id) ON DELETE CASCADE`, `lead_id → leads(id)`, `decision_maker_id → decision_makers(id)`, audit user FKs.

**Relationships:**

- N—1 with `outreach_campaigns`.
- N—1 with `decision_makers` (actual recipient).
- N—1 with `leads` (context).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| campaign_id | BIGINT | No | Parent campaign |
| lead_id | BIGINT | Yes | Context lead |
| decision_maker_id | BIGINT | No | Recipient contact |
| member_status | VARCHAR(30) | No | CHECK: QUEUED, SENDING, SENT, OPENED, CLICKED, REPLIED, BOUNCED, UNSUBSCRIBED, OPTED_OUT, FAILED, SKIPPED |
| sequence_step | SMALLINT | No | Current step (1-based) |
| is_last_step | BOOLEAN | No | Sequence complete |
| personalization_payload | JSONB | Yes | Variable substitutions applied |
| tracked_links | JSONB | Yes | Per-link click tracking |
| scheduled_at | TIMESTAMPTZ | Yes | Next send window |
| sent_at | TIMESTAMPTZ | Yes | First send time |
| opened_at | TIMESTAMPTZ | Yes | First open |
| replied_at | TIMESTAMPTZ | Yes | First reply |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `uq_campaign_members__campaign__decision_maker` unique on `(campaign_id, decision_maker_id)`
- `ix_campaign_members__campaign_id__member_status`
- `ix_campaign_members__scheduled_at`

---

### 7.3 `emails`

**Purpose:** Stores all outbound and inbound email messages sent through campaigns or individually, with provider tracking, delivery state, and threading.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `campaign_id → outreach_campaigns(id)`, `campaign_member_id → campaign_members(id)`, `lead_id → leads(id)`, `company_id → companies(id)`, `decision_maker_id → decision_makers(id)`, `from_user_id → users(id)`, `in_reply_to_email_id → emails(id)` (self), `lead_activity_id → lead_activities(id)`, audit user FKs.

**Relationships:**

- N—1 with `decision_makers`, `leads`, `campaigns`.
- 1—1 optional with `lead_activities` (automatic activity row).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| campaign_id | BIGINT | Yes | Parent campaign |
| campaign_member_id | BIGINT | Yes | Parent campaign member |
| lead_id | BIGINT | Yes | Context lead |
| company_id | BIGINT | Yes | Context company |
| decision_maker_id | BIGINT | Yes | Recipient |
| direction | VARCHAR(10) | No | CHECK: OUTBOUND, INBOUND |
| email_type | VARCHAR(30) | No | CHECK: COLD, FOLLOW_UP, REPLY, PROPOSAL, NURTURE, INTERNAL_NOTE, OTHER |
| from_user_id | BIGINT | No | Sending user |
| to_email | VARCHAR(255) | No | Primary recipient |
| cc_emails | JSONB | Yes | CC list |
| bcc_emails | JSONB | Yes | BCC list |
| subject | VARCHAR(500) | Yes | Subject |
| body_text | TEXT | Yes | Plain text body |
| body_html | TEXT | Yes | HTML body |
| provider | VARCHAR(30) | Yes | SENDGRID, SES, BREVO, GMAIL, SMTP, OTHER |
| provider_message_id | VARCHAR(255) | Yes | Provider message id |
| thread_id | VARCHAR(255) | Yes | Thread grouping id |
| in_reply_to_email_id | BIGINT | Yes | Parent email in thread |
| status | VARCHAR(30) | No | CHECK: DRAFT, QUEUED, SENDING, SENT, DELIVERED, OPENED, CLICKED, BOUNCED, FAILED, UNSUBSCRIBED, SPAM |
| delivered_at | TIMESTAMPTZ | Yes | Delivery time |
| opened_at | TIMESTAMPTZ | Yes | First open |
| clicked_at | TIMESTAMPTZ | Yes | First click |
| bounced_at | TIMESTAMPTZ | Yes | Bounce time |
| bounced_reason | VARCHAR(255) | Yes | Bounce classification |
| spam_score | NUMERIC(5,2) | Yes | Spam score 0–100 |
| lead_activity_id | BIGINT | Yes | Generated activity row |
| error_payload | JSONB | Yes | Provider error details |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |

**Indexes:**

- `uq_emails__provider_message_id` unique partial `WHERE provider_message_id IS NOT NULL`
- `ix_emails__decision_maker_id__created_at` (descending)
- `ix_emails__campaign_id`
- `ix_emails__status__created_at`
- `ix_emails__thread_id`
- `ix_emails__lead_activity_id` unique partial

**Constraints:**

- `CHECK (status IN ('DRAFT','QUEUED','SENDING','SENT','DELIVERED','OPENED','CLICKED','BOUNCED','FAILED','UNSUBSCRIBED','SPAM'))`
- `CHECK (direction IN ('OUTBOUND','INBOUND'))`

---

### 7.4 `linkedin_messages`

**Purpose:** Stores LinkedIn engagement: connection requests, connection notes, direct messages, profile visits, and inbound replies.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `campaign_id → outreach_campaigns(id)`, `campaign_member_id → campaign_members(id)`, `lead_id → leads(id)`, `company_id → companies(id)`, `decision_maker_id → decision_makers(id)`, `from_user_id → users(id)`, `lead_activity_id → lead_activities(id)`, audit user FKs.

**Relationships:**

- N—1 with `decision_makers`, `leads`, `campaigns`.
- 1—1 optional with `lead_activities`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| campaign_id | BIGINT | Yes | Parent campaign |
| campaign_member_id | BIGINT | Yes | Parent campaign member |
| lead_id | BIGINT | Yes | Context lead |
| company_id | BIGINT | Yes | Context company |
| decision_maker_id | BIGINT | No | Target contact |
| direction | VARCHAR(10) | No | CHECK: OUTBOUND, INBOUND |
| message_type | VARCHAR(30) | No | CHECK: CONNECTION_REQUEST, CONNECTION_NOTE, MESSAGE, COMMENT, PROFILE_VIEW, OTHER |
| from_user_id | BIGINT | No | Sending user |
| body | TEXT | Yes | Message text |
| media_url | VARCHAR(500) | Yes | Attached media |
| provider | VARCHAR(30) | No | LINKEDIN_API, LINKEDIN_WEB, MANUAL, OTHER |
| provider_thread_urn | VARCHAR(255) | Yes | LinkedIn thread URN |
| provider_message_urn | VARCHAR(255) | Yes | LinkedIn message URN |
| status | VARCHAR(30) | No | CHECK: DRAFT, QUEUED, SENT, DELIVERED, READ, REPLIED, FAILED, RATE_LIMITED, WITHDRAWN |
| connection_status | VARCHAR(20) | No | NONE, REQUEST_PENDING, CONNECTED |
| sent_at | TIMESTAMPTZ | Yes | Send time |
| delivered_at | TIMESTAMPTZ | Yes | Delivery time |
| read_at | TIMESTAMPTZ | Yes | First read |
| replied_at | TIMESTAMPTZ | Yes | First reply |
| failed_reason | VARCHAR(255) | Yes | Failure details |
| lead_activity_id | BIGINT | Yes | Generated activity row |
| error_payload | JSONB | Yes | Provider error details |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |

**Indexes:**

- `uq_linkedin_messages__provider_message_urn` unique partial
- `uq_linkedin_messages__provider_thread_urn` unique partial
- `ix_linkedin_messages__decision_maker_id__created_at` (descending)
- `ix_linkedin_messages__campaign_id`
- `ix_linkedin_messages__status__created_at`

**Constraints:**

- `CHECK (status IN ('DRAFT','QUEUED','SENT','DELIVERED','READ','REPLIED','FAILED','RATE_LIMITED','WITHDRAWN'))`
- `CHECK (message_type IN ('CONNECTION_REQUEST','CONNECTION_NOTE','MESSAGE','COMMENT','PROFILE_VIEW','OTHER'))`

---

### 7.5 `whatsapp_messages`

**Purpose:** Stores WhatsApp Business conversations: messages, templates, media, and interactive payloads with delivery/read receipts.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `campaign_id → outreach_campaigns(id)`, `campaign_member_id → campaign_members(id)`, `lead_id → leads(id)`, `company_id → companies(id)`, `decision_maker_id → decision_makers(id)`, `from_user_id → users(id)`, `lead_activity_id → lead_activities(id)`, audit user FKs.

**Relationships:**

- N—1 with `decision_makers`, `leads`, `campaigns`.
- 1—1 optional with `lead_activities`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| campaign_id | BIGINT | Yes | Parent campaign |
| campaign_member_id | BIGINT | Yes | Parent campaign member |
| lead_id | BIGINT | Yes | Context lead |
| company_id | BIGINT | Yes | Context company |
| decision_maker_id | BIGINT | No | Target contact |
| direction | VARCHAR(10) | No | CHECK: OUTBOUND, INBOUND |
| message_type | VARCHAR(30) | No | CHECK: TEXT, TEMPLATE, MEDIA, INTERACTIVE, BUTTON |
| from_user_id | BIGINT | No | Sending user |
| body | TEXT | Yes | Message text |
| media_url | VARCHAR(500) | Yes | Media link |
| template_name | VARCHAR(150) | Yes | WhatsApp template name |
| template_language | VARCHAR(20) | Yes | Template language code |
| template_params | JSONB | Yes | Template variable values |
| provider | VARCHAR(30) | No | TWILIO, GUPSHUP, META_WHATSAPP, OTHER |
| provider_message_id | VARCHAR(255) | Yes | Provider message id |
| wa_phone_profile | VARCHAR(50) | Yes | Sending WhatsApp number |
| status | VARCHAR(30) | No | CHECK: DRAFT, QUEUED, SENT, DELIVERED, READ, REPLIED, FAILED, UNSUBSCRIBED, OPTED_OUT |
| sent_at | TIMESTAMPTZ | Yes | Send time |
| delivered_at | TIMESTAMPTZ | Yes | Delivery time |
| read_at | TIMESTAMPTZ | Yes | First read |
| replied_at | TIMESTAMPTZ | Yes | First reply |
| lead_activity_id | BIGINT | Yes | Generated activity row |
| error_payload | JSONB | Yes | Provider error details |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |

**Indexes:**

- `uq_whatsapp_messages__provider_message_id` unique partial
- `ix_whatsapp_messages__decision_maker_id__created_at` (descending)
- `ix_whatsapp_messages__campaign_id`
- `ix_whatsapp_messages__status__created_at`

**Constraints:**

- `CHECK (status IN ('DRAFT','QUEUED','SENT','DELIVERED','READ','REPLIED','FAILED','UNSUBSCRIBED','OPTED_OUT'))`
- `CHECK (message_type IN ('TEXT','TEMPLATE','MEDIA','INTERACTIVE','BUTTON'))`

---

### 7.6 `follow_up_tasks`

**Purpose:** Stores scheduled and completed follow-up actions (calls, emails, meetings, reviews) assigned to BD users, linked to leads/deals/contacts, with reminders and recurrence.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `lead_id → leads(id)`, `company_id → companies(id)`, `decision_maker_id → decision_makers(id)`, `deal_id → deals(id)`, `assigned_to_user_id → users(id)`, `created_by_user_id → users(id)`, `parent_task_id → follow_up_tasks(id)` (self), `related_activity_id → lead_activities(id)`, audit user FKs.

**Relationships:**

- N—1 with `leads`, `deals`, `decision_makers`, `users`.
- Optional 1—N self-referencing for recurring task chains.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| lead_id | BIGINT | Yes | Context lead |
| company_id | BIGINT | Yes | Context company |
| decision_maker_id | BIGINT | Yes | Context contact |
| deal_id | BIGINT | Yes | Context deal |
| task_type | VARCHAR(30) | No | CHECK: CALL, EMAIL, LINKEDIN, WHATSAPP, MEETING, PROPOSAL_FOLLOWUP, REVIEW, ADMIN, OTHER |
| subject | VARCHAR(255) | No | Task title |
| description | TEXT | Yes | Task details |
| channel | VARCHAR(20) | Yes | Preferred channel |
| priority | VARCHAR(10) | No | CHECK: LOW, MEDIUM, HIGH, URGENT |
| status | VARCHAR(20) | No | CHECK: OPEN, IN_PROGRESS, COMPLETED, CANCELLED, MISSED, RESCHEDULED, BLOCKED |
| assigned_to_user_id | BIGINT | No | Assignee |
| due_at | TIMESTAMPTZ | No | Due time |
| completed_at | TIMESTAMPTZ | Yes | Completion time |
| reminder_at | TIMESTAMPTZ | Yes | Reminder time |
| reminder_sent | BOOLEAN | No | Reminder dispatched |
| recurrence_pattern | VARCHAR(20) | No | NONE, DAILY, WEEKLY, MONTHLY |
| parent_task_id | BIGINT | Yes | Recurrence parent |
| related_activity_id | BIGINT | Yes | Resulting activity |
| completion_notes | TEXT | Yes | Outcome notes |
| created_by_user_id | BIGINT | No | Creator |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `ix_follow_up_tasks__assigned_to_user_id__status__due_at`
- `ix_follow_up_tasks__lead_id__status`
- `ix_follow_up_tasks__due_at`
- `ix_follow_up_tasks__deal_id`

**Constraints:**

- `CHECK (task_type IN ('CALL','EMAIL','LINKEDIN','WHATSAPP','MEETING','PROPOSAL_FOLLOWUP','REVIEW','ADMIN','OTHER'))`
- `CHECK (status IN ('OPEN','IN_PROGRESS','COMPLETED','CANCELLED','MISSED','RESCHEDULED','BLOCKED'))`
- `CHECK (recurrence_pattern IN ('NONE','DAILY','WEEKLY','MONTHLY'))`
- `CHECK (due_at IS NOT NULL)`

---

## 8. Deal Pipeline Domain

### 8.1 `deal_pipeline_stages`

**Purpose:** Configurable pipeline stage definitions per organization (e.g. New → Qualified → Proposal → Negotiation → Won/Lost), with ordering, default probability, and terminal flags.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, audit user FKs.

**Relationships:**

- N—1 with `organizations`.
- 1—N with `deals`, `deal_stage_history`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| stage_name | VARCHAR(120) | No | Display name |
| stage_key | VARCHAR(50) | No | Stable key (NEW, QUALIFIED…) |
| stage_order | SMALLINT | No | Sort order |
| category | VARCHAR(30) | No | CHECK: NEW, QUALIFIED, PROPOSAL, NEGOTIATION, WON, LOST, OTHER |
| default_probability | NUMERIC(5,2) | No | Default win probability % |
| is_terminal | BOOLEAN | No | Terminal stage |
| is_won | BOOLEAN | No | Won terminal |
| is_lost | BOOLEAN | No | Lost terminal |
| slack_days | SMALLINT | Yes | Expected days in stage |
| is_active | BOOLEAN | No | Stage enabled |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |

**Indexes:**

- `uq_deal_pipeline_stages__organization__order` unique on `(organization_id, stage_order)`
- `uq_deal_pipeline_stages__organization__key` unique on `(organization_id, stage_key)`

**Constraints:**

- `CHECK (category IN ('NEW','QUALIFIED','PROPOSAL','NEGOTIATION','WON','LOST','OTHER'))`
- `CHECK (default_probability >= 0 AND default_probability <= 100)`
- `CHECK (NOT (is_won = TRUE AND is_lost = TRUE))`

---

### 8.2 `deals`

**Purpose:** Represents active or closed commercial opportunities progressing through the pipeline — the conversion outcome of a lead for a specific warehouse.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `lead_id → leads(id)`, `company_id → companies(id)`, `warehouse_id → warehouses(id)`, `stage_id → deal_pipeline_stages(id)`, `primary_decision_maker_id → decision_makers(id)`, `owner_user_id → users(id)`, `campaign_id → outreach_campaigns(id)`, audit user FKs.

**Relationships:**

- N—1 with `leads`, `companies`, `warehouses`, `deal_pipeline_stages`, `users`, `campaigns`.
- 1—N with `deal_stage_history`, `follow_up_tasks`.

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| public_id | UUID | No | External identifier |
| organization_id | BIGINT | No | Owning tenant |
| deal_name | VARCHAR(255) | No | Deal title |
| lead_id | BIGINT | No | Source lead |
| company_id | BIGINT | No | Prospect company |
| warehouse_id | BIGINT | Yes | Selected warehouse |
| primary_decision_maker_id | BIGINT | Yes | Key contact |
| stage_id | BIGINT | No | Current pipeline stage |
| stage_entered_at | TIMESTAMPTZ | No | When current stage began |
| expected_revenue | NUMERIC(16,2) | No | Expected contract value |
| currency | CHAR(3) | No | Default 'INR' |
| probability | NUMERIC(5,2) | No | Win probability % (defaults from stage) |
| forecast_amount | NUMERIC(16,2) | Yes | Denormalized expected_revenue × probability |
| expected_close_date | DATE | Yes | Projected close |
| deal_status | VARCHAR(20) | No | CHECK: OPEN, WON, LOST, ABANDONED |
| won_at | TIMESTAMPTZ | Yes | Win time |
| lost_at | TIMESTAMPTZ | Yes | Loss time |
| deal_value | NUMERIC(16,2) | Yes | Final value when won |
| win_reason | VARCHAR(255) | Yes | Why won |
| lost_reason | VARCHAR(255) | Yes | Why lost |
| lost_to | VARCHAR(150) | Yes | Competitor/broker |
| abandoned_reason | VARCHAR(255) | Yes | Why abandoned |
| owner_user_id | BIGINT | No | Deal owner |
| campaign_id | BIGINT | Yes | Source campaign |
| was_ai_recommended | BOOLEAN | No | AI-assisted deal |
| ai_insights | JSONB | Yes | AI negotiation/preparation insights |
| created_at | TIMESTAMPTZ | No | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | Last update timestamp |
| created_by_user_id | BIGINT | Yes | Recording user |
| updated_by_user_id | BIGINT | Yes | Last modifying user |

**Indexes:**

- `uq_deals__public_id` unique
- `ix_deals__stage_id__expected_close_date`
- `ix_deals__owner_user_id__deal_status`
- `ix_deals__company_id`
- `ix_deals__lead_id`
- `ix_deals__expected_close_date`
- Partial unique `uq_deals__lead__warehouse` on `(lead_id, warehouse_id) WHERE warehouse_id IS NOT NULL`

**Constraints:**

- `CHECK (deal_status IN ('OPEN','WON','LOST','ABANDONED'))`
- `CHECK (probability >= 0 AND probability <= 100)`
- `CHECK (NOT (won_at IS NOT NULL AND lost_at IS NOT NULL))`

---

### 8.3 `deal_stage_history`

**Purpose:** Immutable audit trail of every pipeline stage movement, with actor, reason, timing, and dwell time — enables funnel analytics and AI learning.

**Primary Key:** `id`

**Foreign Keys:** `organization_id → organizations(id)`, `deal_id → deals(id) ON DELETE CASCADE`, `from_stage_id → deal_pipeline_stages(id)`, `to_stage_id → deal_pipeline_stages(id)`, `changed_by_user_id → users(id)`, audit user FKs.

**Relationships:**

- N—1 with `deals`.
- N—1 with `deal_pipeline_stages` (from/to).

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| id | BIGINT IDENTITY | No | Primary key |
| organization_id | BIGINT | No | Owning tenant |
| deal_id | BIGINT | No | Parent deal |
| from_stage_id | BIGINT | Yes | Previous stage (null = creation) |
| to_stage_id | BIGINT | No | New stage |
| changed_by_user_id | BIGINT | Yes | Actor (null = system/AI) |
| changed_at | TIMESTAMPTZ | No | Movement time |
| change_reason | VARCHAR(255) | Yes | Reason |
| notes | TEXT | Yes | Details |
| days_in_previous_stage | NUMERIC(8,2) | Yes | Dwell time |
| change_trigger | VARCHAR(20) | No | CHECK: MANUAL, AI, SYSTEM, SCHEDULED |
| created_at | TIMESTAMPTZ | No | Creation timestamp |

**Indexes:**

- `ix_deal_stage_history__deal_id__changed_at` (descending)
- `ix_deal_stage_history__to_stage_id__changed_at`
- `ix_deal_stage_history__change_trigger`

---

## 9. Domain → Table Mapping

| # | Platform Capability | Table(s) |
|---|---|---|
| 1 | Companies | `companies`, `company_locations` |
| 2 | Warehouses | `warehouses` |
| 3 | Decision Makers | `decision_makers` |
| 4 | Leads | `leads` |
| 5 | Requirements | `requirements` |
| 6 | Lead Activities | `lead_activities` |
| 7 | Opportunity Signals | `opportunity_signals` (base) |
| 8 | Lead Scoring | `lead_score_snapshots` |
| 9 | Warehouse Matching | `warehouse_matches` |
| 10 | AI Recommendations | `ai_recommendations` |
| 11 | Outreach Campaigns | `outreach_campaigns`, `campaign_members` |
| 12 | Emails | `emails` |
| 13 | LinkedIn Messages | `linkedin_messages` |
| 14 | WhatsApp Messages | `whatsapp_messages` |
| 15 | Follow-up Tasks | `follow_up_tasks` |
| 16 | Deal Pipeline | `deal_pipeline_stages`, `deals`, `deal_stage_history` |
| 17 | Company News | `company_news` |
| 18 | Hiring Signals | `hiring_signals` |
| 19 | Factory Expansion Signals | `factory_expansion_signals` |
| 20 | Import Export Signals | `import_export_signals` |
| 21 | AI Learning History | `ai_learning_history` |

**Supporting/foundation tables:** `organizations`, `users`, `industries`.

---

## 10. Entity Relationships

### 10.1 Relationship Diagram (Logical)

```
organizations
   ├── 1─N users
   ├── 1─N warehouses
   ├── 1─N companies
   ├── 1─N leads
   ├── 1─N requirements
   ├── 1─N outreach_campaigns
   ├── 1─N deal_pipeline_stages
   ├── 1─N deals
   └── 1─N follow_up_tasks

industries
   └── 1─N companies

companies
   ├── 1─N company_locations
   ├── 1─N decision_makers
   ├── 1─N leads
   ├── 1─N opportunity_signals
   ├── 1─N deals
   └── 1─N messages (email / linkedin / whatsapp)

leads
   ├── 1─N requirements
   ├── 1─N lead_activities
   ├── 1─N lead_score_snapshots
   ├── 1─N warehouse_matches
   ├── 1─N opportunity_signals (triggered)
   ├── 1─N ai_recommendations
   ├── 1─N follow_up_tasks
   ├── 1─N messages
   └── 1─N deals

requirements
   ├── 1─N warehouse_matches
   └── 1─N lead_activities (optional requirement context)

opportunity_signals
   ├── 1─1 company_news
   ├── 1─1 hiring_signals
   ├── 1─1 factory_expansion_signals
   └── 1─1 import_export_signals

warehouses
   └── 1─N warehouse_matches

warehouse_matches ── N─1 deals (selected match)

users
   ├── 1─N lead_activities (actor)
   ├── 1─N follow_up_tasks (assignee)
   ├── 1─N deals (owner)
   ├── 1─N campaigns (owner)
   └── 1─N ai_recommendations (acted_by)

outreach_campaigns
   ├── 1─N campaign_members
   ├── 1─N emails
   ├── 1─N linkedin_messages
   └── 1─N whatsapp_messages

campaign_members ── N─1 decision_makers

decision_makers
   ├── 1─N emails
   ├── 1─N linkedin_messages
   ├── 1─N whatsapp_messages
   └── 1─N campaign_members

deals ── 1─N deal_stage_history
```

### 10.2 Key Relationship Narratives

- **Tenant scoping:** every business table belongs to exactly one `organizations` row. Row-Level Security keys off this column.
- **Company → Lead:** a company can produce many leads (one per distinct business opportunity/location).
- **Lead → Requirement:** a lead can carry multiple structured warehouse requirements (`requirements`: multiple cities, expansion phases, product categories). `requirements` is the canonical warehouse-demand record and the primary input to the AI matching engine.
- **Requirement ↔ Warehouse:** resolved through `warehouse_matches`, each of which references a specific `requirements` row (legacy matches without `requirement_id` fall back to the lead-level requirement summary fields).
- **Signal → Lead:** an `opportunity_signals` row may reference the lead it created (`leads.lead_id`); signal subtype detail lives in exactly one of the four subtype tables via a unique 1:1 FK.
- **Message → Activity:** each sent Email/LinkedIn/WhatsApp message optionally creates exactly one `lead_activities` row (`activity_source_type` + `activity_source_id`), so the lead timeline stays unified across channels.
- **Campaign membership:** `campaign_members` resolves campaign ↔ decision-maker, carrying per-member sequence state; recipient messages point to both campaign and member.
- **Pipeline:** `deals` reference a configurable `stage_id`; `deal_stage_history` records every transition immutably.
- **Scoring:** `lead_score_snapshots` are immutable; `leads.ai_score` and `latest_score_snapshot_id` are performance-oriented pointers to the latest snapshot.
- **AI learning:** `ai_learning_history` records every AI call; `ai_recommendations` records the human-facing suggestion; outcomes feed back through `reward_signal`/`ground_truth` for model improvement.

---

## 11. Database Normalization

The design targets **Third Normal Form (3NF)** with selective, documented denormalization.

### 11.1 First Normal Form (1NF)

- Every column holds atomic values; no repeating groups or comma-separated lists.
- Variable multi-value data (preferred cities, amenities, score factors, token usage) is stored in `JSONB`, which is atomic at the column level and only used where the application does not need to join/filter relationally.
- Genuinely relational multi-valued facts are separated into their own tables: `company_locations`, `campaign_members`, `warehouse_matches`, `lead_score_snapshots`, `lead_activities`, `deal_stage_history`.
- Every table has a defined primary key.

### 11.2 Second Normal Form (2NF)

- All primary keys are single-column surrogate `id` keys, so partial-key dependencies are structurally impossible.
- Composite-key tables (`campaign_members`, `warehouse_matches`) have no non-key attribute that depends on only part of the key:
  - `campaign_members.member_status`, `sequence_step`, `scheduled_at` depend on the full `(campaign_id, decision_maker_id)` pair.
  - `warehouse_matches.match_score`, `match_rank`, `status` depend on the full `(lead_id, warehouse_id)` pair.

### 11.3 Third Normal Form (3NF)

- Transitive dependencies are removed:
  - Company data (`industry_id`, `hq_city`) lives in `companies` or `industries`, not repeated in `leads` or `signals`.
  - Stage probability belongs to `deal_pipeline_stages`, not repeated across `deals`.
  - Decision-maker details live only in `decision_makers`; message tables reference the FK.
  - Warehouse attributes live only in `warehouses`; `warehouse_matches` reference the FK.
- No non-key column depends on another non-key column.

### 11.4 Signal Subtyping (Specialization / Class Table Inheritance)

- `opportunity_signals` is the supertype holding common columns (source, timing, confidence, status, dedup).
- `company_news`, `hiring_signals`, `factory_expansion_signals`, `import_export_signals` are subtypes holding type-specific columns, each linked 1:1 via a unique `signal_id` FK.
- This eliminates the sparse-column problem of a single wide signals table, preserves referential integrity, and allows new signal types to be added as new subtype tables without altering the base.

### 11.5 Controlled Denormalization (Deliberate, Documented)

Performance-motivated, application-maintained redundant values with a defined canonical source:

| Denormalized Column | Canonical Source | Reason |
|---|---|---|
| `leads.ai_score` | `lead_score_snapshots.total_score` (latest) | Fast dashboard sorting/filtering |
| `leads.latest_score_snapshot_id` | `lead_score_snapshots` | Direct pointer, avoids MAX() scan |
| `leads.last_activity_at` | `lead_activities.occurred_at` | Timeline/funnel queries without GROUP BY |
| `leads.space_needed_sqft` / `warehouse_type` / `preferred_cities` / `budget_per_month` / `move_in_timeframe` / `lease_tenure_years` | `requirements` (canonical demand detail) | Legacy/summary display on lead list views; new integrations write to `requirements` |
| `deals.forecast_amount` | `expected_revenue × probability` | Report rollups without computation |
| `outreach_campaigns.sent_count / open_count / reply_count` | message & member tables | Campaign stats without COUNT() joins |

All denormalized values are refreshed by application services (or triggers) on the owning event, and are documented so the team does not treat them as independent facts.

### 11.6 Referential Integrity

- Foreign keys enforce integrity at the database level.
- Critical business dependencies use `RESTRICT` (e.g., deleting a company with leads is blocked).
- Pure child details use `CASCADE` (signal subtypes, stage history, `requirements` under `leads`).
- Audit references use `SET NULL` so history survives user deletion.
- Smart unique constraints prevent duplicates: provider message IDs, signal `dedup_hash`, company `domain`, decision-maker `(company_id, email)`, match `(lead_id, warehouse_id)`.

---

## 12. Future Scalability

The schema is designed for hundreds of millions of rows (companies, signals, messages, AI history) with incremental, non-breaking scaling.

### 12.1 Multi-Tenant SaaS Growth

- `organization_id` exists on every business table from day one.
- Production deploys Row-Level Security (RLS) policies: `organization_id = current_setting('app.org_id')`.
- Adding a new tenant requires no schema change.
- Cross-tenant dedup (same target company researched by two tenants) is handled via `companies.domain` + optional global company registry in a future `global_companies` mapping table.

### 12.2 Time-Based Partitioning (High-Volume Tables)

Tables with append-heavy, time-ordered growth are partition candidates:

- `lead_activities`
- `emails`, `linkedin_messages`, `whatsapp_messages`
- `opportunity_signals` (+ subtype tables by `signal_id`)
- `lead_score_snapshots`
- `ai_learning_history`
- `deal_stage_history`

Recommended strategy: PostgreSQL native **range partitioning on `created_at` (monthly)**, with the partitioning key included in all unique/index definitions. This enables:

- Bulk `DETACH PARTITION` archival to cold storage (S3/Parquet) without downtime.
- Fast time-window scans (e.g., last 90 days of activities).
- `ai_learning_history` treated as near-immutable — ideal for append-only partitioning.
- `requirements` is intentionally **not** partition-listed: it is updated by AI scoring writes; focused composite indexes (see §13.1) keep it on the OLTP primary.

### 12.3 Horizontal Scaling

- **Read scale:** read replicas for dashboards, reporting, and AI batch scans; primary handles OLTP writes.
- **Extreme tenant scale (future):** sharding on `organization_id` or Citus-style distributed tables keyed by `organization_id`; all tables already carry it.
- **Connection pooling:** PgBouncer; short-lived transactions by design.

### 12.4 Event-Driven & Analytics

- Change Data Capture (Debezium) can publish inserts from `lead_activities`, `deals`, `deal_stage_history`, `lead_score_snapshots`, and `ai_recommendations` to Kafka.
- Downstream **data warehouse**:
  - `fact_lead_activities`
  - `fact_lead_scores`
  - `fact_lead_requirements`
  - `fact_messages`
  - `fact_signal_events`
  - `fact_deal_stage_history`
  - Dimensions: company, warehouse, requirement, decision_maker, campaign, user, time, geography.
- dbt transformations build funnel, conversion, channel-performance, and forecast models.
- Dashboards query the warehouse or Postgres materialized views, never the OLTP hot path.

### 12.5 AI / ML Platform Evolution

- `ai_learning_history` is the raw event log and training-corpus source.
- `requirements` is the canonical demand input; `warehouse_matches` (requirement-scoped) plus `requirements.ai_match_score` / `priority_score` provide labeled fit and outcome data for the matching engine.
- `lead_score_snapshots` + `warehouse_matches` + `ai_recommendations.status/feedback` provide labeled outcome data for model evaluation, offline metrics, and RLHF-style feedback loops.
- A future feature store can project score factors and signal aggregates into vectors without schema changes (JSONB payloads already structured).

### 12.6 Capability Extensibility

- **New signal types:** add a new subtype table 1:1 to `opportunity_signals`; base untouched.
- **New channels (SMS, voice, portal):** add a new message-type table following the `emails` pattern; unified timeline preserved via `lead_activities.activity_source_type/id`.
- **New score dimensions:** extend `lead_score_snapshots.score_factors` JSONB; version bump via `score_version`.
- **New campaign types:** extend reusable `outreach_campaigns` with `campaign_type`.
- **Globalization:** `currency` columns already exist; locale/language columns can be added per tenant without structural change.

### 12.7 Data Retention & Archiving

- Partitioned history tables archived by month after configurable retention.
- AI raw input/output payloads can be purged to object storage while `ai_learning_history` metadata remains searchable.
- Soft-delete on master data prevents accidental loss; hard purge via scheduled jobs.

---

## 13. Performance Considerations

### 13.1 Indexing Strategy

- **Every foreign key is indexed** to support join paths and cascade enforcement.
- **Composite indexes** match real query patterns, not single columns:
  - Lead workspace: `(organization_id, status, owner_user_id)`
  - Requirement workspace & AI prioritization: `(organization_id, requirement_status, priority_score)`; `ai_match_score` descending
  - Follow-ups: `(assigned_to_user_id, status, due_at)`
  - Timeline: `(lead_id, occurred_at DESC) INCLUDE (activity_type, subject, summary)`
  - Pipeline: `(stage_id, expected_close_date)`
  - Signals: `(company_id, detected_at DESC)`
- **Partial indexes** keep hot indexes small:
  - `WHERE is_deleted = FALSE` on master tables
  - `WHERE provider_message_id IS NOT NULL` on message provider IDs
  - `WHERE agent_name = 'signal_scanner'` on `ai_learning_history.input_hash`
- **Trigram GIN** on `companies.company_name` for fuzzy company searching before Elasticsearch is introduced.
- **JSONB GIN** on `company_news.key_entities` and flag columns (`hiring_signals.warehouse_relevant`, `import_export_signals.needs_warehousing`).
- **Geospatial (PostGIS upgrade):** convert `latitude/longitude` pairs on `warehouses` and `company_locations` to `geography` columns and create GiST indexes for radius/distance matching — the core of `warehouse_matches`.

### 13.2 Query Hot Paths

| Hot Query | Supporting Design |
|---|---|
| Lead dashboard (status, owner, score) | Composite index + denormalized `ai_score`, `last_activity_at` |
| Requirement detail & AI prioritization | `requirements` composite `(organization_id, requirement_status, priority_score)`; `ai_match_score` (desc) |
| Lead timeline | Covering index on `lead_activities (lead_id, occurred_at)` |
| Open follow-ups for today | Index `(assigned_to_user_id, status, due_at)` |
| Pipeline forecast by stage | Index `(stage_id, expected_close_date)`; `forecast_amount` precomputed |
| Signal inbox by type/status | Index `(signal_type, status)` + `detected_at` |
| Latest score per lead | `leads.latest_score_snapshot_id` pointer |
| Campaign stats | Denormalized counters on `outreach_campaigns` |

### 13.3 Denormalization Trade-Offs

Controlled redundancy (Section 11.5) eliminates the most expensive aggregation queries (MAX scores, COUNT messages, SUM forecasts) from the primary read path. Updates happen on write events; consistency is enforced by application transactions and validated by periodic reconciliation jobs.

### 13.4 Write Path Optimization

- Message, activity, signal, and AI-learning tables are **append-heavy** and partition-ready; consider `UNLOGGED` staging tables for high-volume AI ingestion if durability can be relaxed, then bulk-load into partitioned tables.
- `ai_learning_history.input_context/output_payload` JSONB writes are large; keep them out of secondary indexes to reduce bloat.
- Batch inserts (AI scanners) use `COPY` or multi-row inserts within a single transaction; `dedup_hash` unique constraint prevents duplicates safely.

### 13.5 Maintenance & Operations

- Tune `autovacuum` aggressively for high-write tables (activities, messages, AI history) to prevent bloat; JSONB updates (`updated_at`) are the main bloat source.
- Use `pg_repack` where needed; prefer `UPDATE`-heavy tables to carry only small mutable payloads.
- Enable `pg_stat_statements` to continuously tune the index set.
- Keyset pagination (`WHERE id > :last_id ORDER BY id`) instead of `OFFSET` for deep pages on timeline/activity/message queries.
- Read replicas serve reports/dashboards; primary serves user-facing OLTP.

### 13.6 Cache Layer (Redis — future)

- Pipeline stage definitions and industry lookups: read-through cache, invalidated on change.
- Lead list page (page 1) for high-traffic dashboards: warm cache with 60–120s TTL.
- Signal dedup shortlist: in-memory LRU of recent `dedup_hash` values to skip duplicate AI scans.
- Never cache scoring snapshots or message status as source of truth.

### 13.7 Application-Level Guardrails

- Use `SELECT IN (…)`/`JOIN` batching instead of N+1 (especially leads → activities/scoring).
- Requirement lists eager-load the parent lead and latest `warehouse_matches`; never lazy-load per-row score columns in list screens.
- Use `selectinload`/`joinedload` for known aggregates; avoid lazy-loading JSONB payloads on list screens.
- All list endpoints enforce tenant scoping (`organization_id`) at the query level, backed by RLS.

---

## 14. Summary

This schema delivers a normalized, tenant-isolated, AI-native foundation that:

1. Distinguishes the platform's own customers (`organizations`) from researched prospects (`companies`).
2. Models warehouse supply (`warehouses`) and warehouse demand (`leads` + `requirements`) as first-class citizens, with `requirements` as the primary input for the AI matching engine.
3. Captures every business signal through a normalized supertype/subtype model that is trivially extensible.
4. Makes AI explainable and auditable through immutable scoring snapshots, recommendation records, and a complete AI learning history.
5. Unifies all outreach channels under campaign + message structures with a single lead timeline.
6. Supports a configurable deal pipeline with immutable stage history.
7. Is built for millions of rows through partitioning, composite/partial indexing, controlled denormalization, and clear read/write path separation.
8. Elevates each client warehouse requirement to a first-class, structured record (`requirements`) that carries location, technical, financial, timeline, status, and AI score detail per lead.

---

© Bhoodevi Warehouse — Confidential