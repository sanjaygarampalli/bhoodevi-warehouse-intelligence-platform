"""Add organization memberships.

Revision ID: l7d8e9f0a1b2
Revises: k6c7d8e9f0a1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "l7d8e9f0a1b2"
down_revision = "k6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade():
    role = postgresql.ENUM("OWNER", "ADMIN", "MANAGER", "MEMBER", "VIEWER", name="organizationmemberrole")
    membership_status = postgresql.ENUM("ACTIVE", "INACTIVE", name="membershipstatus")
    role_column = postgresql.ENUM(
        "OWNER", "ADMIN", "MANAGER", "MEMBER", "VIEWER",
        name="organizationmemberrole", create_type=False,
    )
    membership_status_column = postgresql.ENUM(
        "ACTIVE", "INACTIVE", name="membershipstatus", create_type=False,
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        role.create(bind, checkfirst=True)
        membership_status.create(bind, checkfirst=True)
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", role_column, nullable=False),
        sa.Column("status", membership_status_column, nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_org_memberships__user__organization"),
    )
    op.create_index("ix_org_memberships__organization__status", "organization_memberships", ["organization_id", "status"])
    op.create_index("ix_org_memberships__user__status", "organization_memberships", ["user_id", "status"])


def downgrade():
    op.drop_table("organization_memberships")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        postgresql.ENUM(name="membershipstatus").drop(bind, checkfirst=True)
        postgresql.ENUM(name="organizationmemberrole").drop(bind, checkfirst=True)