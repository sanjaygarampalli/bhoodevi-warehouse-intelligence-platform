"""Add canonical requirement candidate CRM conversions."""
from alembic import op
import sqlalchemy as sa

revision = "d94e21f0a1b2"
down_revision = "c76810bece01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "requirement_candidate_conversions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requirement_candidate_id", sa.Integer(), sa.ForeignKey("requirement_candidates.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("requirements.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "CONVERTED", "FAILED", name="requirementcandidateconversionstatus"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status <> 'CONVERTED' OR (company_id IS NOT NULL AND lead_id IS NOT NULL AND requirement_id IS NOT NULL)",
            name="ck_rcc__converted_records_complete",
        ),
        sa.UniqueConstraint("requirement_candidate_id", name="uq_rcc__requirement_candidate"),
        sa.UniqueConstraint("lead_id", name="uq_rcc__lead"),
        sa.UniqueConstraint("requirement_id", name="uq_rcc__requirement"),
    )
    op.create_index("ix_rcc__organization__status", "requirement_candidate_conversions", ["organization_id", "status"])


def downgrade():
    op.drop_index("ix_rcc__organization__status", table_name="requirement_candidate_conversions")
    op.drop_table("requirement_candidate_conversions")
    op.execute("DROP TYPE IF EXISTS requirementcandidateconversionstatus")