"""Record ORM index alignment after historical indexes were verified."""

from alembic import op


revision = "r3d4e5f6a7b8"
down_revision = "q2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    # All intended workloads are already covered by historical indexes:
    # - ix_lead_activities__deal_id__activity_date__id covers deal filtering
    #   and the repository's activity_date/id ordering.
    # - ix_lead_activities__decision_maker_id is the established single-column
    #   index created by f1a2b3c4d5e6.
    # - ix_warehouses__organization_id is the established single-column index
    #   created by o0a1b2c3d4e5.
    pass


def downgrade():
    pass