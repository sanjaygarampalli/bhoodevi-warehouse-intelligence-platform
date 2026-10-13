# BHOODEVI Warehouse Intelligence Platform (BWIP)

> Empowering warehouse businesses with AI-driven intelligence to discover, qualify, and convert genuine business opportunities.

---

## Overview

BHOODEVI Warehouse Intelligence Platform (BWIP) is an AI-powered Warehouse Demand Intelligence Platform designed to help warehouse owners, logistics companies, industrial developers, and business development teams identify, manage, and convert warehouse opportunities into long-term customers.

Unlike traditional Warehouse Management Systems (WMS), BWIP focuses on generating new business rather than managing existing warehouse operations.

---

## Vision

To become the most trusted AI platform for warehouse business development by enabling data-driven decisions, intelligent lead discovery, and automated customer acquisition.

---

## Mission

Our mission is to help warehouse businesses:

- Discover genuine warehouse demand
- Find verified decision-makers
- Track business opportunities
- Automate business development
- Increase warehouse occupancy
- Build long-term customer relationships

---

## Core Modules

### Lead Intelligence Agent
Discover companies requiring warehouse space.

### Company Intelligence Agent
Research organizations, industries, and expansion plans.

### Decision Maker Agent
Identify verified contacts and key decision-makers.

### Tender Intelligence Agent
Monitor government and private warehouse tenders.

### CRM Agent
Manage leads, interactions, and follow-ups.

### Proposal Agent
Generate professional proposals and quotations.

### Analytics Agent
Provide dashboards and business insights.

---

## Target Industries

- Logistics & 3PL
- FMCG
- Manufacturing
- Food Processing
- Pharmaceuticals
- Solar & Renewable Energy
- Steel
- Cement
- E-commerce
- Government Organizations

---

## Technology Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- AI Agents
- REST APIs
- Docker
- GitHub
- Visual Studio Code

---

## Project Structure

```
src/
docs/
tests/
data/
assets/
scripts/
requirements/
logs/
prompts/
```

---

## Development Status

Current Phase:

**Foundation & Product Design**

### F4 local browser QA data

F4 has a manual, idempotent development-only data path for exercising the real
authentication, organization-membership, market-signal list, and signal-detail
flows. It refuses to run unless `APP_ENV=development`, is never called by
application startup, and does not create data in staging or production.

Set `BWIP_F4_DEV_PASSWORD` in the current local process to a password of at
least eight characters, then run:

```powershell
.venv\Scripts\python.exe scripts\seed_f4_dev.py
```

Use the printed development email with `POST /auth/login` through the normal
OAuth2 password flow. Do not put the password or token in source, URLs, logs,
or reports. The script reuses rows identified by its fixed local-development
email, organization code, company name, and signal title. To clean the data,
stop local services and remove the rows for organization code `F4QADEV` (the
organization cascades its memberships and market signals); do not run the
cleanup against a non-development database.

Upcoming Milestones:

1. Product Documentation
2. System Architecture
3. Database Design
4. AI Agent Development
5. MVP
6. SaaS Platform

---

## Repository

BWIP is being developed as a scalable AI-powered SaaS platform for the warehousing industry.

---

## License

Proprietary

© Bhoodevi Warehouse