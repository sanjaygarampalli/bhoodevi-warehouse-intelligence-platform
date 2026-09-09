"""add organization_id to companies table

Revision ID: g2e3d4c5b6a7
Revises: f1e2d3c4b5a6
Create Date: 2026-08-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g2e3d4c5b6a7"
down_revision: Union[str, Sequence[str], None] = "f1e2d3c4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "companies",
        sa.Column(
            "organization_id",
            sa.Integer(),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_companies__organization_id"),
        "companies",
        ["organization_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_companies__organization_id",
        "companies",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_companies__organization_id",
        "companies",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_companies__organization_id"),
        table_name="companies",
    )
    op.drop_column("companies", "organization_id")
