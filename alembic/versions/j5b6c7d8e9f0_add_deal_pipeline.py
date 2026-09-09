"""Add configurable Deal stages, commercial opportunities and stage history.

Revision ID: j5b6c7d8e9f0
Revises: i4a5b6c7d8e9
"""
from alembic import op
import sqlalchemy as sa

revision = "j5b6c7d8e9f0"
down_revision = "i4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deal_pipeline_stages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stage_name", sa.String(120), nullable=False),
        sa.Column("stage_key", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_terminal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_won", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_lost", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "stage_key", name="uq_deal_pipeline_stages__organization__key"),
        sa.UniqueConstraint("organization_id", "stage_order", name="uq_deal_pipeline_stages__organization__order"),
        sa.CheckConstraint("stage_order >= 0", name="ck_deal_pipeline_stages__order"),
        sa.CheckConstraint(
            "(is_terminal AND ((is_won AND NOT is_lost) OR (is_lost AND NOT is_won))) "
            "OR (NOT is_terminal AND NOT is_won AND NOT is_lost)", name="ck_deal_pipeline_stages__terminal",
        ),
    )
    op.create_index("ix_deal_pipeline_stages_organization_id", "deal_pipeline_stages", ["organization_id"])
    op.create_table(
        "deals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("deal_name", sa.String(255), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("requirements.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("selected_warehouse_match_id", sa.Integer(), sa.ForeignKey("warehouse_matches.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("stage_id", sa.Integer(), sa.ForeignKey("deal_pipeline_stages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stage_entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_revenue", sa.Numeric(16, 2), nullable=True),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deal_status", sa.String(20), server_default="OPEN", nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("deal_status IN ('OPEN','WON','LOST')", name="ck_deals__status"),
        sa.CheckConstraint(
            "(deal_status = 'OPEN' AND closed_at IS NULL) OR "
            "(deal_status IN ('WON','LOST') AND closed_at IS NOT NULL)", name="ck_deals__closure",
        ),
        sa.CheckConstraint("expected_revenue >= 0", name="ck_deals__expected_revenue"),
        sqlite_autoincrement=True,
    )
    for field in ("lead_id", "requirement_id", "selected_warehouse_match_id"):
        op.create_index(f"ix_deals_{field}", "deals", [field])
    op.create_index("ix_deals__stage_id__expected_close_date", "deals", ["stage_id", "expected_close_date"])
    op.create_index("ix_deals__organization__status", "deals", ["organization_id", "deal_status"])
    op.create_index("uq_deals__open_requirement", "deals", ["requirement_id"], unique=True,
                    sqlite_where=sa.text("deal_status = 'OPEN'"), postgresql_where=sa.text("deal_status = 'OPEN'"))
    op.create_table(
        "deal_stage_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_stage_id", sa.Integer(), sa.ForeignKey("deal_pipeline_stages.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("to_stage_id", sa.Integer(), sa.ForeignKey("deal_pipeline_stages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_stage_key", sa.String(50), nullable=True),
        sa.Column("from_stage_name", sa.String(120), nullable=True),
        sa.Column("to_stage_key", sa.String(50), nullable=False),
        sa.Column("to_stage_name", sa.String(120), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("change_reason", sa.String(255), nullable=True),
        sa.CheckConstraint("from_stage_id IS NULL OR from_stage_id <> to_stage_id", name="ck_deal_stage_history__different_stages"),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_deal_stage_history__deal_id__changed_at", "deal_stage_history", ["deal_id", "changed_at", "id"])
    for field in ("from_stage_id", "to_stage_id", "changed_by_user_id"):
        op.create_index(f"ix_deal_stage_history_{field}", "deal_stage_history", [field])


def downgrade():
    op.drop_table("deal_stage_history")
    op.drop_table("deals")
    op.drop_table("deal_pipeline_stages")