"""Add tenant-scoped warehouse capabilities and company requirements."""
from alembic import op
import sqlalchemy as sa

revision = "o0a1b2c3d4e5"
down_revision = "n9f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("warehouses", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.create_index("ix_warehouses__organization_id", "warehouses", ["organization_id"])
    op.create_foreign_key("fk_warehouses__organization_id", "warehouses", "organizations", ["organization_id"], ["id"], ondelete="RESTRICT")
    json_type = sa.JSON()
    op.create_table(
        "warehouse_capability_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("capabilities", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "warehouse_id", name="uq_warehouse_capability_profile_org_warehouse"),
    )
    op.create_index("ix_warehouse_capability_profiles__organization_id", "warehouse_capability_profiles", ["organization_id"])
    op.create_index("ix_warehouse_capability_profiles__warehouse_id", "warehouse_capability_profiles", ["warehouse_id"])
    op.create_table(
        "company_warehouse_requirement_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirements", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "company_id", name="uq_company_warehouse_requirement_profile_org_company"),
    )
    op.create_index("ix_company_warehouse_requirement_profiles__organization_id", "company_warehouse_requirement_profiles", ["organization_id"])
    op.create_index("ix_company_warehouse_requirement_profiles__company_id", "company_warehouse_requirement_profiles", ["company_id"])


def downgrade() -> None:
    op.drop_table("company_warehouse_requirement_profiles")
    op.drop_table("warehouse_capability_profiles")
    op.drop_constraint("fk_warehouses__organization_id", "warehouses", type_="foreignkey")
    op.drop_index("ix_warehouses__organization_id", table_name="warehouses")
    op.drop_column("warehouses", "organization_id")