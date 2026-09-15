"""Add explicit commercial outcome evidence to Deals."""

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    lost_reason = sa.Enum(
        "PRICE", "LOCATION", "WAREHOUSE_FIT", "AVAILABILITY", "TIMING",
        "COMPETITOR", "CUSTOMER_CANCELLED", "REQUIREMENT_CHANGED", "NO_RESPONSE",
        "NOT_QUALIFIED", "OTHER", name="lostreasoncategory",
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        lost_reason.create(bind, checkfirst=True)
    op.add_column("deals", sa.Column("lost_reason_category", lost_reason, nullable=True))
    op.add_column("deals", sa.Column("final_commercial_amount", sa.Numeric(16, 2), nullable=True))
    op.add_column("deals", sa.Column("final_commercial_currency", sa.String(3), nullable=True))
    op.add_column("deals", sa.Column("final_lease_duration_months", sa.Integer(), nullable=True))
    op.add_column("deals", sa.Column("outcome_notes", sa.Text(), nullable=True))
    op.add_column("deals", sa.Column("closure_evidence_reference", sa.String(255), nullable=True))
    op.create_index("ix_deals__lost_reason_category", "deals", ["lost_reason_category"])


def downgrade():
    op.drop_index("ix_deals__lost_reason_category", table_name="deals")
    for column in ("closure_evidence_reference", "outcome_notes", "final_lease_duration_months",
                   "final_commercial_currency", "final_commercial_amount", "lost_reason_category"):
        op.drop_column("deals", column)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="lostreasoncategory").drop(bind, checkfirst=True)