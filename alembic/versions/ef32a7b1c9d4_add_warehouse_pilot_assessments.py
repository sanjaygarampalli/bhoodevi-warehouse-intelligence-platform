"""Add canonical persisted Warehouse Pilot assessments."""

from alembic import op
import sqlalchemy as sa


revision = "ef32a7b1c9d4"
down_revision = "d94e21f0a1b2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "warehouse_pilot_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assessed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("capability_profile_id", sa.Integer(), sa.ForeignKey("warehouse_capability_profiles.id", ondelete="RESTRICT")),
        sa.Column("company_requirement_profile_id", sa.Integer(), sa.ForeignKey("company_warehouse_requirement_profiles.id", ondelete="RESTRICT")),
        sa.Column("operational_profile_id", sa.Integer(), sa.ForeignKey("warehouse_operational_profiles.id", ondelete="RESTRICT")),
        sa.Column("commercial_profile_id", sa.Integer(), sa.ForeignKey("warehouse_commercial_profiles.id", ondelete="RESTRICT")),
        sa.Column("requirement_assessment_id", sa.Integer(), sa.ForeignKey("warehouse_requirement_assessments.id", ondelete="RESTRICT")),
        sa.Column("evaluation_version", sa.String(length=30), nullable=False, server_default="v1"),
        sa.Column("overall_classification", sa.String(length=50), nullable=False),
        sa.Column("result_snapshot", sa.JSON(), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_wpa__organization__assessed_at", "warehouse_pilot_assessments", ["organization_id", "assessed_at"])
    op.create_index("ix_wpa__company__assessed_at", "warehouse_pilot_assessments", ["company_id", "assessed_at"])
    op.create_index("ix_wpa__warehouse__assessed_at", "warehouse_pilot_assessments", ["warehouse_id", "assessed_at"])
    op.create_index("ix_warehouse_pilot_assessments_organization_id", "warehouse_pilot_assessments", ["organization_id"])
    op.create_index("ix_warehouse_pilot_assessments_company_id", "warehouse_pilot_assessments", ["company_id"])
    op.create_index("ix_warehouse_pilot_assessments_warehouse_id", "warehouse_pilot_assessments", ["warehouse_id"])
    op.create_index("ix_warehouse_pilot_assessments_assessed_by_user_id", "warehouse_pilot_assessments", ["assessed_by_user_id"])
    op.create_index("ix_warehouse_pilot_assessments_overall_classification", "warehouse_pilot_assessments", ["overall_classification"])


def downgrade():
    for name in (
        "ix_warehouse_pilot_assessments_overall_classification",
        "ix_warehouse_pilot_assessments_assessed_by_user_id",
        "ix_warehouse_pilot_assessments_warehouse_id",
        "ix_warehouse_pilot_assessments_company_id",
        "ix_warehouse_pilot_assessments_organization_id",
        "ix_wpa__warehouse__assessed_at",
        "ix_wpa__company__assessed_at",
        "ix_wpa__organization__assessed_at",
    ):
        op.drop_index(name, table_name="warehouse_pilot_assessments")
    op.drop_table("warehouse_pilot_assessments")