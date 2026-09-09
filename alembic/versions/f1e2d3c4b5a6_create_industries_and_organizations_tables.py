"""create industries and organizations tables

Revision ID: f1e2d3c4b5a6
Revises: e9f0a1b2c3d4
Create Date: 2026-08-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f1e2d3c4b5a6"
down_revision: Union[str, Sequence[str], None] = "e9f0a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "industries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_industries__code"),
        sa.UniqueConstraint("name", name="uq_industries__name"),
    )
    op.create_index(
        op.f("ix_industries__category"),
        "industries",
        ["category"],
        unique=False,
    )

    orgtype = postgresql.ENUM(
        "SOLE_PROPRIETOR",
        "PARTNERSHIP",
        "LLP",
        "PVT_LTD",
        "PUBLIC_LTD",
        "GOVT",
        "OTHER",
        name="orgtype",
        create_type=False,
    )
    orgtype.create(op.get_bind(), checkfirst=True)

    subscription_tier = postgresql.ENUM(
        "FREE", "STARTER", "GROWTH", "ENTERPRISE",
        name="subscriptiontier",
        create_type=False,
    )
    subscription_tier.create(op.get_bind(), checkfirst=True)

    organization_status = postgresql.ENUM(
        "TRIAL", "ACTIVE", "SUSPENDED", "CANCELLED",
        name="organizationstatus",
        create_type=False,
    )
    organization_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("org_code", sa.String(length=20), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("trading_name", sa.String(length=255), nullable=True),
        sa.Column("org_type", orgtype, nullable=False),
        sa.Column("industry_id", sa.Integer(), nullable=True),
        sa.Column("gstin", sa.String(length=15), nullable=True),
        sa.Column("pan", sa.String(length=10), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column(
            "country", sa.String(length=100),
            nullable=False,
            server_default=sa.text("'India'::text"),
        ),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("subscription_tier", subscription_tier, nullable=False),
        sa.Column("status", organization_status, nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["industry_id"], ["industries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_organizations__public_id"),
        sa.UniqueConstraint("org_code", name="uq_organizations__org_code"),
        sa.CheckConstraint(
            "email IS NULL OR email LIKE '%@%'",
            name="ck_organizations__email",
        ),
        sa.CheckConstraint(
            "status IN ('TRIAL','ACTIVE','SUSPENDED','CANCELLED')",
            name="ck_organizations__status",
        ),
        sa.CheckConstraint(
            "org_type IN ('SOLE_PROPRIETOR','PARTNERSHIP','LLP','PVT_LTD','PUBLIC_LTD','GOVT','OTHER')",
            name="ck_organizations__orgtype",
        ),
    )
    op.create_index(
        op.f("uq_organizations__gstin"),
        "organizations",
        ["gstin"],
        unique=True,
        postgresql_where=sa.text("gstin IS NOT NULL"),
    )
    op.create_index(
        op.f("uq_organizations__pan"),
        "organizations",
        ["pan"],
        unique=True,
        postgresql_where=sa.text("pan IS NOT NULL"),
    )
    op.create_index(
        op.f("ix_organizations__city"),
        "organizations",
        ["city"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_organizations__orgtype", "organizations", type_="check",
    )
    op.drop_constraint(
        "ck_organizations__status", "organizations", type_="check",
    )
    op.drop_constraint(
        "ck_organizations__email", "organizations", type_="check",
    )
    op.drop_constraint(
        "uq_organizations__public_id", "organizations", type_="unique",
    )
    op.drop_constraint(
        "uq_organizations__org_code", "organizations", type_="unique",
    )
    op.drop_index(op.f("ix_organizations__city"), table_name="organizations")
    op.drop_index(op.f("uq_organizations__pan"), table_name="organizations")
    op.drop_index(op.f("uq_organizations__gstin"), table_name="organizations")

    op.drop_table("organizations")

    orgtype = postgresql.ENUM(
        "SOLE_PROPRIETOR", "PARTNERSHIP", "LLP",
        "PVT_LTD", "PUBLIC_LTD", "GOVT", "OTHER",
        name="orgtype",
        create_type=False,
    )
    orgtype.drop(op.get_bind(), checkfirst=True)

    subscription_tier = postgresql.ENUM(
        "FREE", "STARTER", "GROWTH", "ENTERPRISE",
        name="subscriptiontier",
        create_type=False,
    )
    subscription_tier.drop(op.get_bind(), checkfirst=True)

    organization_status = postgresql.ENUM(
        "TRIAL", "ACTIVE", "SUSPENDED", "CANCELLED",
        name="organizationstatus",
        create_type=False,
    )
    organization_status.drop(op.get_bind(), checkfirst=True)

    op.drop_constraint("uq_industries__name", "industries", type_="unique")
    op.drop_constraint("uq_industries__code", "industries", type_="unique")
    op.drop_index(op.f("ix_industries__category"), table_name="industries")
    op.drop_table("industries")
