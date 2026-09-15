"""Add optional Deal and DecisionMaker links to LeadActivity."""

from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "ef32a7b1c9d4"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE activitytype ADD VALUE IF NOT EXISTS 'SITE_VISIT'")
        op.execute("ALTER TYPE activitytype ADD VALUE IF NOT EXISTS 'NEGOTIATION'")
    else:
        # SQLite stores SQLAlchemy Enum values as strings; no type alteration is needed.
        pass

    with op.batch_alter_table("lead_activities") as batch:
        batch.add_column(sa.Column("deal_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("decision_maker_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_lead_activities__deal_id", "deals", ["deal_id"], ["id"], ondelete="RESTRICT")
        batch.create_foreign_key("fk_lead_activities__decision_maker_id", "decision_makers", ["decision_maker_id"], ["id"], ondelete="RESTRICT")

    op.create_index("ix_lead_activities__deal_id__activity_date__id", "lead_activities", ["deal_id", "activity_date", "id"])
    op.create_index("ix_lead_activities__decision_maker_id", "lead_activities", ["decision_maker_id"])


def downgrade():
    op.drop_index("ix_lead_activities__decision_maker_id", table_name="lead_activities")
    op.drop_index("ix_lead_activities__deal_id__activity_date__id", table_name="lead_activities")
    with op.batch_alter_table("lead_activities") as batch:
        batch.drop_constraint("fk_lead_activities__decision_maker_id", type_="foreignkey")
        batch.drop_constraint("fk_lead_activities__deal_id", type_="foreignkey")
        batch.drop_column("decision_maker_id")
        batch.drop_column("deal_id")
    # PostgreSQL enum values cannot be removed safely in a portable downgrade.