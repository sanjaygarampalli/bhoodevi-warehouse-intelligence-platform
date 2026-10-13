"""Align older pilot snapshot storage with the existing JSONB model contract."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "u6f7a8b9c0d1"
down_revision = "t5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        for column in ("result_snapshot", "source_snapshot"):
            op.alter_column("warehouse_pilot_assessments", column,
                            existing_type=sa.JSON(), type_=postgresql.JSONB(),
                            existing_nullable=False, postgresql_using=f"{column}::jsonb")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for column in ("result_snapshot", "source_snapshot"):
            op.alter_column("warehouse_pilot_assessments", column,
                            existing_type=postgresql.JSONB(), type_=sa.JSON(),
                            existing_nullable=False, postgresql_using=f"{column}::json")
