"""Add human-controlled contact investigation and outreach workflow."""
from alembic import op
import sqlalchemy as sa

revision = "p1b2c3d4e5f6"
# The repository currently contains two pre-existing migration branches.  This
# forward-only Module 18 migration joins them before adding its tables.
down_revision = ("b657ffadfdac", "b8c9d0e1f2a3")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("contact_investigations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("company_contacts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("investigated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("investigation_status", sa.String(30), nullable=False, server_default="NOT_REVIEWED"),
        *[sa.Column(name, sa.Boolean()) for name in ("designation_verified", "department_verified", "seniority_verified", "email_verified", "phone_verified", "linkedin_verified", "still_employed", "relevant_to_warehouse_decisions", "potential_decision_maker")],
        sa.Column("research_notes", sa.Text()), sa.Column("selected_for_outreach", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contact_investigations_org_company_contact", "contact_investigations", ["organization_id", "company_id", "contact_id"])
    op.create_table("contact_outreach_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer(), sa.ForeignKey("company_contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("performed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("method", sa.String(20), nullable=False), sa.Column("performed_at", sa.DateTime(), nullable=False),
        sa.Column("purpose", sa.String(255)), sa.Column("summary", sa.Text()), sa.Column("outcome", sa.String(30)), sa.Column("response_status", sa.String(50)), sa.Column("next_action", sa.Text()), sa.Column("next_follow_up_at", sa.DateTime()), sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contact_outreach_org_company_contact_time", "contact_outreach_activities", ["organization_id", "company_id", "contact_id", "performed_at", "created_at", "id"])


def downgrade():
    op.drop_index("ix_contact_outreach_org_company_contact_time", table_name="contact_outreach_activities")
    op.drop_table("contact_outreach_activities")
    op.drop_index("ix_contact_investigations_org_company_contact", table_name="contact_investigations")
    op.drop_table("contact_investigations")