# Organization Access Control

## Model

BWIP retains its existing JWT authentication and global `User.role` field. Organization access is represented separately by `OrganizationMembership`, which links a user to an organization and stores an `OWNER`, `ADMIN`, `MANAGER`, `MEMBER`, or `VIEWER` role plus an `ACTIVE`/`INACTIVE` status. `(user_id, organization_id)` is unique, so membership changes are updates rather than duplicate rows.

## Policy

- Global users with `User.role == "admin"` retain system-wide access, including membership administration.
- Active owners and admins may administer membership.
- Owners, admins, managers, and members have organization write access.
- Viewers have organization read access only.
- Inactive or missing memberships receive HTTP 403 for organization-context requests.
- Authentication failures continue to return HTTP 401 through the existing dependency.

Membership administration uses `GET`, `POST`, `PATCH`, and soft-deactivation `DELETE` routes under `/organizations/{organization_id}/members`.

## Intelligence scoping

Organization IDs supplied to the prioritization, operational dashboard, and action intelligence APIs are authorization checked before service execution. Lead intelligence is scoped through the existing `Lead -> Company -> Organization` relationship. Deals and pipeline stages use their existing direct organization foreign keys. Follow-ups, requirements, activities, and matches are scoped through their lead relationship.

Requests without `organization_id` preserve the existing backward-compatible behavior. This is intentionally a migration step: callers should adopt an organization context before the legacy database-wide reads are tightened.

Warehouses currently belong to users (`owner_id`) and have no organization foreign key. They are not assigned to an organization by this feature; organization-specific warehouse authorization remains a documented limitation rather than an invented relationship.

## Migration and limitations

The membership table is created by Alembic revision `l7d8e9f0a1b2`. Existing users are not automatically assigned memberships because the repository has no authoritative mapping from historical users to organizations. A controlled bootstrap/backfill is required before relying exclusively on membership-scoped legacy endpoints. Membership changes are not added to a new audit system; BWIP has no shared audit service suitable for this small foundation.