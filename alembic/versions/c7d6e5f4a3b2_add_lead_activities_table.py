"""add lead activities table

Revision ID: c7d6e5f4a3b2
Revises: f0e1d2c3b4a5
Create Date: 2026-08-05 18:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d6e5f4a3b2'
down_revision: Union[str, Sequence[str], None] = 'f0e1d2c3b4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('lead_activities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('lead_id', sa.Integer(), nullable=False),
    sa.Column('activity_type', sa.Enum('CALL', 'EMAIL', 'LINKEDIN', 'WHATSAPP', 'MEETING', 'NOTE', 'TASK', 'SYSTEM_EVENT', 'AI_ACTION', 'SIGNAL', 'PROPOSAL', 'OTHER', name='activitytype'), nullable=False),
    sa.Column('subject', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('activity_date', sa.DateTime(), nullable=False),
    sa.Column('next_followup_date', sa.DateTime(), nullable=True),
    sa.Column('status', sa.Enum('SCHEDULED', 'COMPLETED', 'CANCELLED', name='activitystatus'), nullable=False),
    sa.Column('outcome', sa.Enum('COMPLETED', 'NO_ANSWER', 'LEFT_VOICEMAIL', 'INTERESTED', 'NOT_INTERESTED', 'CALLBACK_SCHEDULED', 'BOUNCED', 'FAILED', 'OTHER', name='activityoutcome'), nullable=True),
    sa.Column('performed_by', sa.Integer(), nullable=True),
    sa.Column('channel', sa.Enum('EMAIL', 'LINKEDIN', 'WHATSAPP', 'PHONE', 'FACE_TO_FACE', 'SYSTEM', name='activitychannel'), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=True),
    sa.Column('activity_source_type', sa.Enum('EMAIL', 'LINKEDIN', 'WHATSAPP', 'TASK', 'SYSTEM', name='activitysourcetype'), nullable=True),
    sa.Column('activity_source_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
    sa.ForeignKeyConstraint(['performed_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lead_activities_activity_type'), 'lead_activities', ['activity_type'], unique=False)
    op.create_index(op.f('ix_lead_activities_id'), 'lead_activities', ['id'], unique=False)
    op.create_index(op.f('ix_lead_activities_lead_id'), 'lead_activities', ['lead_id'], unique=False)
    op.create_index(op.f('ix_lead_activities_performed_by'), 'lead_activities', ['performed_by'], unique=False)
    op.create_index(op.f('ix_lead_activities_status'), 'lead_activities', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_lead_activities_status'), table_name='lead_activities')
    op.drop_index(op.f('ix_lead_activities_performed_by'), table_name='lead_activities')
    op.drop_index(op.f('ix_lead_activities_lead_id'), table_name='lead_activities')
    op.drop_index(op.f('ix_lead_activities_id'), table_name='lead_activities')
    op.drop_index(op.f('ix_lead_activities_activity_type'), table_name='lead_activities')
    op.drop_table('lead_activities')