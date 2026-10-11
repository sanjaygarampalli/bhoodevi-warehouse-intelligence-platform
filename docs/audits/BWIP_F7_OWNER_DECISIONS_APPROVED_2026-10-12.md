# BWIP F7 Owner Decision Record — Approved

- **Decision record date:** 2026-10-12
- **Decision status:** D1–D10 approved by explicit owner instruction
- **Unresolved decisions:** None reported
- **F7 contact-method interface:** Approved
- **Additional conditions:** None specified
- **Implementation authorization:** Decision-level Phase B gate is satisfied. No implementation is authorized or performed by this record.

## Explicitly approved architecture decisions

| ID | Approved option | Decision |
|---|---|---|
| D1 | A | Tenant-local person identity. |
| D2 | A | Configurable 90/365-day freshness thresholds. |
| D3 | B | MANAGER+ verification; OWNER/ADMIN resolution. |
| D4 | A | Preserve legacy records and map them. |
| D5 | A | F7 is read-only for contact methods; F8 owns verification. |
| D6 | A | External source keys are review-gated. |
| D7 | A | Resolve duplicates per record. |
| D8 | A | Use a canonical service with legacy projections. |
| D9 | A | Synthetic-only backfill until sign-off. |
| D10 | A | Typed evidence tables with direct foreign keys. |

## Related approvals and boundaries

1. **F7 contact-method interface:** Explicitly approved. F7 may expose the agreed read-only interface; F8 remains responsible for contact-method verification.
2. **Backfill:** Only synthetic-data backfill is permitted until the required isolated rehearsal and sign-off are complete. This does not authorize production or real-customer backfill.
3. **Additional conditions:** None specified by the owner.
4. **Unselected decisions:** No approval is inferred for any option or decision not explicitly selected above.
5. **Implementation boundary:** This is an architecture decision record only. No application code, migrations, database state, or runtime configuration is changed by this record.

## Phase B authorization-gate determination

**Decision-level gate: SATISFIED.** The owner has explicitly approved all ten decisions (D1–D10), reported no unresolved decisions, approved the F7 contact-method interface, and specified no additional conditions. D9 explicitly retains the synthetic-only backfill restriction pending sign-off.

**Execution preflight remains mandatory.** Before implementation starts, the implementer must verify the current repository/worktree state, preserve all pre-existing changes, confirm the agreed F7 scope and acceptance criteria, and ensure any isolated migration/backfill rehearsal and sign-off required by D9 occur before non-synthetic backfill. This record does not claim those operational checks have already been performed.

## Audit note

This record reflects the owner's explicit instruction received on 2026-10-12. It supersedes the earlier status in which D1–D10 were all marked PROPOSED. It does not authorize implementation in this task; the requested action here is to record the decisions and assess the gate only.
