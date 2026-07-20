# Database Design

**Product:** BHOODEVI Warehouse Intelligence Platform (BWIP)

**Document:** Database Design

**Version:** 0.1.0-alpha

**Status:** Draft

**Last Updated:** July 2026

---

# Purpose

This document defines the logical database design for BWIP.

The database is designed to support a scalable, multi-user, AI-powered warehouse business development platform.

---

# Database Technology

Primary Database

- PostgreSQL

Future Support

- Redis (Caching)
- Elasticsearch (Search)
- Data Warehouse (Analytics)

---

# Core Design Principles

The database should be:

- Normalized
- Secure
- Scalable
- Auditable
- Cloud Ready

---

# Core Entities

## User

Stores platform users.

Fields:

- User ID
- Name
- Email
- Password Hash
- Phone
- Role
- Status
- Created Date

---

## Organization

Represents a company using BWIP.

Fields:

- Organization ID
- Company Name
- Industry
- GST Number
- Address
- Website

---

## Warehouse

Stores warehouse information.

Fields:

- Warehouse ID
- Organization ID
- Warehouse Name
- Location
- Total Area
- Built-up Area
- Storage Type
- Availability
- Monthly Rent
- Status

---

## Company

Represents potential customers.

Fields:

- Company ID
- Company Name
- Industry
- Website
- Headquarters
- Business Description
- Source

---

## Contact

Stores decision makers.

Fields:

- Contact ID
- Company ID
- Name
- Designation
- Email
- Phone
- LinkedIn
- Verification Status

---

## Lead

Represents a business opportunity.

Fields:

- Lead ID
- Company ID
- Warehouse Requirement
- Lead Source
- Priority
- Status
- AI Score
- Created Date

---

## Opportunity

Represents qualified business opportunities.

Fields:

- Opportunity ID
- Lead ID
- Expected Revenue
- Probability
- Stage
- Expected Closing Date

---

## Proposal

Stores generated proposals.

Fields:

- Proposal ID
- Opportunity ID
- Proposal Date
- Version
- Status

---

## Activity

Tracks business activities.

Fields:

- Activity ID
- User ID
- Lead ID
- Activity Type
- Notes
- Date

---

## Follow-up

Stores scheduled follow-ups.

Fields:

- Follow-up ID
- Lead ID
- Assigned User
- Follow-up Date
- Status

---

## AI Recommendation

Stores AI-generated recommendations.

Fields:

- Recommendation ID
- Lead ID
- AI Agent
- Recommendation
- Confidence Score
- Created Date

---

# Relationships

Organization
    └── Warehouse

Company
    ├── Contact
    ├── Lead
    └── Opportunity

Lead
    ├── Activity
    ├── Follow-up
    └── Proposal

User
    ├── Activity
    └── Follow-up

---

# Audit Requirements

Every major table should include:

- Created By
- Created Date
- Updated By
- Updated Date

Soft delete support should be included where appropriate.

---

# Future Expansion

Future versions may introduce:

- Tenant
- Subscription
- Invoice
- Payment
- Notification
- API Keys
- Integrations

---

# Guiding Principle

The database should support millions of records without requiring major redesign.

---

© Bhoodevi Warehouse