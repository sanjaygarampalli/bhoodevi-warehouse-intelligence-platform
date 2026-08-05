"""add decision makers table

Revision ID: a1b2c3d4e5f6
Revises: 2d5dc7a7d3e6
Create Date: 2026-08-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '2d5dc7a7d3e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('decision_makers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('designation', sa.String(length=255), nullable=False),
    sa.Column('decision_level', sa.Enum('C_SUITE', 'VP', 'DIRECTOR', 'MANAGER', 'EXECUTIVE', 'OTHER', name='decisionlevel'), nullable=False),
    sa.Column('preferred_contact', sa.Enum('EMAIL', 'PHONE', 'LINKEDIN', 'WHATSAPP', name='preferredcontact'), nullable=True),
    sa.Column('decision_maker_status', sa.Enum('NEW', 'CONTACTED', 'RESPONDED', 'QUALIFIED', 'CONVERTED', 'DISQUALIFIED', name='decisionmakerstatus'), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=30), nullable=True),
    sa.Column('linkedin_url', sa.String(length=255), nullable=True),
    sa.Column('is_primary_contact', sa.Boolean(), nullable=False),
    sa.Column('last_contacted_at', sa.DateTime(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_decision_makers_company_id'), 'decision_makers', ['company_id'], unique=False)
    op.create_index(op.f('ix_decision_makers_email'), 'decision_makers', ['email'], unique=False)
    op.create_index(op.f('ix_decision_makers_id'), 'decision_makers', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_decision_makers_id'), table_name='decision_makers')
    op.drop_index(op.f('ix_decision_makers_email'), table_name='decision_makers')
    op.drop_index(op.f('ix_decision_makers_company_id'), table_name='decision_makers')
    op.drop_table('decision_makers')