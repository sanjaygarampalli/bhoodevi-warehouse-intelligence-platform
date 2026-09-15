"""Add canonical warehouse intelligence opportunity conversions."""
from alembic import op
import sqlalchemy as sa

revision = "c76810bece01"
down_revision = "b657ffadfdac"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "warehouse_intelligence_opportunity_conversions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_type", sa.Enum("WAREHOUSE_MATCH", "CAPABILITY_MATCH", "WAREHOUSE_PILOT", name="warehouseintelligenceconversionsource"), nullable=False),
        sa.Column("warehouse_match_id", sa.Integer(), sa.ForeignKey("warehouse_matches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("deal_id", sa.Integer(), sa.ForeignKey("deals.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "CONVERTED", "REJECTED", "FAILED", name="warehouseintelligenceconversionstatus"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source_type = 'WAREHOUSE_MATCH' AND warehouse_match_id IS NOT NULL", name="ck_wioc__supported_source"),
        sa.CheckConstraint("status <> 'CONVERTED' OR deal_id IS NOT NULL", name="ck_wioc__converted_deal"),
        sa.UniqueConstraint("warehouse_match_id", name="uq_wioc__warehouse_match"),
        sa.UniqueConstraint("deal_id", name="uq_wioc__deal"),
    )
    op.create_index("ix_wioc__organization", "warehouse_intelligence_opportunity_conversions", ["organization_id"])
    op.create_index("ix_wioc__organization__status", "warehouse_intelligence_opportunity_conversions", ["organization_id", "status"])
    op.create_index("ix_wioc__source_type__source", "warehouse_intelligence_opportunity_conversions", ["source_type", "warehouse_match_id"])


def downgrade():
    op.drop_table("warehouse_intelligence_opportunity_conversions")
    op.execute("DROP TYPE IF EXISTS warehouseintelligenceconversionstatus")
    op.execute("DROP TYPE IF EXISTS warehouseintelligenceconversionsource")