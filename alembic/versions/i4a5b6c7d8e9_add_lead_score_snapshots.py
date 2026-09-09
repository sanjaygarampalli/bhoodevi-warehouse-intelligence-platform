"""Add rule-based lead score history.

Revision ID: i4a5b6c7d8e9
Revises: h3f4e5d6c7b8
Create Date: 2026-09-09 16:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "i4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "h3f4e5d6c7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lead_score_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        # Owned by the leads migration; never create or drop the shared type here.
        sa.Column("priority", postgresql.ENUM(
            "LOW", "MEDIUM", "HIGH", "URGENT", name="leadpriority", create_type=False,
        ), nullable=False),
        sa.Column("scoring_version", sa.String(30), nullable=False),
        sa.Column("reasons", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "total_score >= 0 AND total_score <= 100",
            name="ck_lead_score_snapshots__total_score_range",
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sqlite_autoincrement=True,
    )
    op.create_index(
        "ix_lead_score_snapshots__lead_id__calculated_at",
        "lead_score_snapshots", ["lead_id", "calculated_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_lead_score_snapshots__lead_id__calculated_at", table_name="lead_score_snapshots")
    op.drop_table("lead_score_snapshots")