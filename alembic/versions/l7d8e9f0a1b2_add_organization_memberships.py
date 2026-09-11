"""Add organization memberships.

Revision ID: l7d8e9f0a1b2
Revises: k6c7d8e9f0a1
"""
from alembic import op
import sqlalchemy as sa

revision = "l7d8e9f0a1b2"
down_revision = "k6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade():
    role = sa.Enum("OWNER", "ADMIN", "MANAGER", "MEMBER", "VIEWER", name="organizationmemberrole")
    membership_status = sa.Enum("ACTIVE", "INACTIVE", name="membershipstatus")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        role.create(bind, checkfirst=True)
        membership_status.create(bind, checkfirst=True)
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("status", membership_status, nullable=False, server_default="ACTIVE"),
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
        sa.Enum(name="membershipstatus").drop(bind, checkfirst=True)
        sa.Enum(name="organizationmemberrole").drop(bind, checkfirst=True)