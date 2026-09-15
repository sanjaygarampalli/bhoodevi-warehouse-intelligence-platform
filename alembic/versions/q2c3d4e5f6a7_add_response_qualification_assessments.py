"""Add human-controlled response qualification assessments."""
from alembic import op
import sqlalchemy as sa

revision = "q2c3d4e5f6a7"
down_revision = "p1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "response_qualification_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("company_contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outreach_activity_id", sa.Integer(), sa.ForeignKey("contact_outreach_activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("observed_facts", sa.JSON(), nullable=False),
        sa.Column("commercial_inference", sa.Text()),
        sa.Column("recommendation", sa.String(50), nullable=False),
        sa.Column("uncertainty", sa.JSON(), nullable=False),
        sa.Column("warehouse_details", sa.JSON(), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("human_review_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_response_qualification_org_company", "response_qualification_assessments", ["organization_id", "company_id"])
    op.create_index("ix_response_qualification_outreach", "response_qualification_assessments", ["outreach_activity_id"])


def downgrade():
    op.drop_index("ix_response_qualification_outreach", table_name="response_qualification_assessments")
    op.drop_index("ix_response_qualification_org_company", table_name="response_qualification_assessments")
    op.drop_table("response_qualification_assessments")