"""add organization_id to companies table

Revision ID: g2e3d4c5b6a7
Revises: f1e2d3c4b5a6
Create Date: 2026-08-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g2e3d4c5b6a7"
down_revision: Union[str, Sequence[str], None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "companies",
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Existing installations already contain companies. Assign those legacy
    # rows to one deterministic, valid organization before enforcing the
    # organization-scoped schema. The DO block is also emitted by offline SQL
    # generation, while the data-dependent checks execute on PostgreSQL.
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                legacy_organization_id INTEGER;
            BEGIN
                SELECT id
                INTO legacy_organization_id
                FROM organizations
                WHERE org_code = 'LEGACY'
                LIMIT 1;

                IF legacy_organization_id IS NULL THEN
                    INSERT INTO organizations (
                        public_id,
                        org_code,
                        legal_name,
                        org_type,
                        subscription_tier,
                        status,
                        country
                    )
                    VALUES (
                        '00000000-0000-0000-0000-000000000001',
                        'LEGACY',
                        'Legacy Companies Organization',
                        'OTHER'::orgtype,
                        'FREE'::subscriptiontier,
                        'ACTIVE'::organizationstatus,
                        'India'
                    )
                    ON CONFLICT DO NOTHING;

                    SELECT id
                    INTO legacy_organization_id
                    FROM organizations
                    WHERE org_code = 'LEGACY'
                       OR public_id = '00000000-0000-0000-0000-000000000001'
                    ORDER BY (org_code = 'LEGACY') DESC
                    LIMIT 1;
                END IF;

                IF legacy_organization_id IS NULL THEN
                    RAISE EXCEPTION
                        'Unable to obtain a valid legacy organization for companies';
                END IF;

                UPDATE companies
                SET organization_id = legacy_organization_id
                WHERE organization_id IS NULL;

                IF EXISTS (
                    SELECT 1
                    FROM companies
                    WHERE organization_id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'Companies organization_id backfill left NULL values';
                END IF;
            END $$;
            """
        )
    )
    op.alter_column(
        "companies",
        "organization_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_index(
        op.f("ix_companies__organization_id"),
        "companies",
        ["organization_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_companies__organization_id",
        "companies",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_companies__organization_id",
        "companies",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_companies__organization_id"),
        table_name="companies",
    )
    op.drop_column("companies", "organization_id")
