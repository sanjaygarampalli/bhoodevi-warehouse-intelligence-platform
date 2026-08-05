"""add leads table

Revision ID: f0e1d2c3b4a5
Revises: a1b2c3d4e5f6
Create Date: 2026-08-05 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0e1d2c3b4a5'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('leads',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('lead_number', sa.String(length=30), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('NEW', 'DISCOVERED', 'CONTACTED', 'QUALIFIED', 'POSITIONED', 'NEGOTIATING', 'WON', 'LOST', 'DISQUALIFIED', 'DORMANT', name='leadstatus'), nullable=False),
    sa.Column('lead_source', sa.Enum('AI_DISCOVERY', 'LINKEDIN', 'WEBSITE', 'IMPORT_EXPORT', 'GOOGLE_MAPS', 'TENDER', 'BROKER', 'REFERRAL', 'MANUAL', 'OTHER', name='leadsource'), nullable=False),
    sa.Column('space_needed_sqft', sa.Numeric(14, 2), nullable=True),
    sa.Column('requirement_type', sa.String(length=30), nullable=True),
    sa.Column('target_industry', sa.String(length=100), nullable=True),
    sa.Column('preferred_city', sa.String(length=100), nullable=True),
    sa.Column('preferred_state', sa.String(length=100), nullable=True),
    sa.Column('preferred_country', sa.String(length=100), nullable=True),
    sa.Column('expected_monthly_rent', sa.Numeric(14, 2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('move_in_timeframe', sa.Enum('IMMEDIATE', '1_3_MONTHS', '3_6_MONTHS', '6_12_MONTHS', 'FLEXIBLE', name='moveintimeframe'), nullable=True),
    sa.Column('lease_tenure_years', sa.Integer(), nullable=True),
    sa.Column('owner_user_id', sa.Integer(), nullable=True),
    sa.Column('primary_decision_maker_id', sa.Integer(), nullable=True),
    sa.Column('ai_score', sa.Numeric(5, 2), nullable=True),
    sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='leadpriority'), nullable=False),
    sa.Column('last_activity_at', sa.DateTime(), nullable=True),
    sa.Column('next_follow_up_at', sa.DateTime(), nullable=True),
    sa.Column('disqualified_reason', sa.String(length=150), nullable=True),
    sa.Column('closed_reason', sa.String(length=150), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('ai_score >= 0 AND ai_score <= 100', name='ck_leads_ai_score_range'),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['primary_decision_maker_id'], ['decision_makers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_company_id'), 'leads', ['company_id'], unique=False)
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)
    op.create_index(op.f('ix_leads_lead_number'), 'leads', ['lead_number'], unique=True)
    op.create_index(op.f('ix_leads_owner_user_id'), 'leads', ['owner_user_id'], unique=False)
    op.create_index(op.f('ix_leads_primary_decision_maker_id'), 'leads', ['primary_decision_maker_id'], unique=False)
    op.create_index(op.f('ix_leads_status'), 'leads', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_leads_status'), table_name='leads')
    op.drop_index(op.f('ix_leads_primary_decision_maker_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_owner_user_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_lead_number'), table_name='leads')
    op.drop_index(op.f('ix_leads_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_company_id'), table_name='leads')
    op.drop_table('leads')