"""Align Organization industry deletion and lookup indexes.

Revision ID: h3f4e5d6c7b8
Revises: g2e3d4c5b6a7
Create Date: 2026-09-09 12:00:00.000000

The original unnamed FK receives organizations_industry_id_fkey on PostgreSQL.
Keep the original revision intact so existing installations receive this repair.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "h3f4e5d6c7b8"
down_revision: Union[str, Sequence[str], None] = "g2e3d4c5b6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "organizations_industry_id_fkey", "organizations", type_="foreignkey"
    )
    op.create_foreign_key(
        "organizations_industry_id_fkey", "organizations", "industries",
        ["industry_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_organizations__industry_id", "organizations", ["industry_id"])
    op.create_index("ix_organizations__legal_name", "organizations", ["legal_name"])


def downgrade() -> None:
    op.drop_index("ix_organizations__legal_name", table_name="organizations")
    op.drop_index("ix_organizations__industry_id", table_name="organizations")
    op.drop_constraint(
        "organizations_industry_id_fkey", "organizations", type_="foreignkey"
    )
    op.create_foreign_key(
        "organizations_industry_id_fkey", "organizations", "industries",
        ["industry_id"], ["id"],
    )