# Company Intelligence & Lead Discovery Foundation

This module adds organization-scoped warehouse-demand intelligence around the existing `Company` master entity. It uses deterministic operational scoring and never labels a rule-based result as AI.

`CompanyIntelligenceProfile` stores optional firmographics, geography, and traceable indicator summaries. `CompanyWarehouseProfile` stores dependency, normalized use cases, area estimates, confidence, and notes. `CompanyContact` and `CompanyContactMethod` are normalized contact records. Contact methods are unique per contact, method type, and normalized value; verification is explicit and only `VERIFIED` methods count as verified.

ICP scoring is the transparent sum of an industry-profile factor (35), expansion-indicator factor (35), and verified market-signal factor (10 per signal, capped at 30), capped at 100. Classifications are POOR 0–19, LOW 20–39, MODERATE 40–59, GOOD 60–79, and EXCELLENT 80–100.

Opportunity scoring is `30% ICP + 25% warehouse fit + 20% verified demand + 10% geography + 15% best contact quality`, rounded and capped at 100. Priorities are CRITICAL at 80+, HIGH at 60–79, MEDIUM at 35–59, otherwise LOW. Factor explanations and the formula are stored.

The engine references existing Market Signals without duplication. Only `VERIFIED` signals linked to the same organization and company contribute ICP and opportunity demand points (10 per ICP signal; 35 per opportunity signal, each capped at their respective maximum). DETECTED, UNDER_REVIEW, REJECTED, and ARCHIVED contribute zero.

GET endpoints return the currently stored profile, assessment, and action rows and never recalculate or write. POST `/recalculate` commands persist the current deterministic result. LOW priority returns `NO_ACTION`; HIGH/CRITICAL with a verified method returns `CONTACT_IMMEDIATELY`; HIGH/CRITICAL without one returns `FIND_DECISION_MAKER`; lower evidence without usable contact returns `RESEARCH_COMPANY`; otherwise `MONITOR_EXPANSION` is recommended. A missing warehouse profile is a deliberate 404.

API reads require active organization membership and writes/recalculation require existing organization write roles. Services validate company ownership and all records are organization-scoped where applicable. This is not predictive modeling, automatic verification, ingestion, scraping, scheduling, or lead conversion. PostgreSQL migration rehearsal and production-data validation remain required.