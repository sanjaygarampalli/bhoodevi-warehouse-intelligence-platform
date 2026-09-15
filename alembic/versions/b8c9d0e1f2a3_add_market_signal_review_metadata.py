"""Add review metadata to market signals.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

from alembic import op
import sqlalchemy as sa


revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("market_signals", sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True))
    op.add_column("market_signals", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("market_signals", sa.Column("review_notes", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_market_signals__reviewed_by_user",
        "market_signals",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_market_signals__reviewed_by_user", "market_signals", type_="foreignkey")
    op.drop_column("market_signals", "review_notes")
    op.drop_column("market_signals", "reviewed_at")
    op.drop_column("market_signals", "reviewed_by_user_id")