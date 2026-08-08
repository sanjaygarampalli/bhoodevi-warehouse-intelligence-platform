"""add requirements table

Revision ID: d8e9f0a1b2c3
Revises: c7d6e5f4a3b2
Create Date: 2026-08-08 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'c7d6e5f4a3b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('requirements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('lead_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('required_builtup_area', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('required_open_area', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('minimum_area', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('maximum_area', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('industry', sa.String(length=100), nullable=True),
    sa.Column('goods_type', sa.String(length=100), nullable=True),
    sa.Column('storage_type', sa.String(length=50), nullable=True),
    sa.Column('compliance_requirements', sa.Text(), nullable=True),
    sa.Column('preferred_state', sa.String(length=100), nullable=True),
    sa.Column('preferred_city', sa.String(length=100), nullable=True),
    sa.Column('preferred_locality', sa.String(length=150), nullable=True),
    sa.Column('preferred_pincode', sa.String(length=10), nullable=True),
    sa.Column('radius_km', sa.Numeric(precision=8, scale=2), nullable=True),
    sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
    sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
    sa.Column('budget_per_sqft', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('lease_duration_months', sa.Integer(), nullable=True),
    sa.Column('security_deposit_months', sa.Integer(), nullable=True),
    sa.Column('preferred_lease_type', sa.String(length=30), nullable=True),
    sa.Column('escalation_percentage', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('warehouse_type', sa.Enum('COVERED', 'OPEN_YARD', 'COLD_STORAGE', 'BONDED', 'MULTIPURPOSE', 'CONTAINER', 'TRANSIT', 'OTHER', name='warehousetype'), nullable=True),
    sa.Column('required_clear_height', sa.Numeric(precision=8, scale=2), nullable=True),
    sa.Column('required_floor_load', sa.Numeric(precision=8, scale=2), nullable=True),
    sa.Column('required_power_load', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('required_docks', sa.Integer(), nullable=True),
    sa.Column('truck_parking_required', sa.Boolean(), nullable=True),
    sa.Column('rail_connectivity_required', sa.Boolean(), nullable=True),
    sa.Column('fire_noc_required', sa.Boolean(), nullable=True),
    sa.Column('temperature_controlled', sa.Boolean(), nullable=True),
    sa.Column('loading_bays_required', sa.Integer(), nullable=True),
    sa.Column('dock_level_required', sa.Boolean(), nullable=True),
    sa.Column('ground_level_required', sa.Boolean(), nullable=True),
    sa.Column('office_required', sa.Boolean(), nullable=True),
    sa.Column('labour_required', sa.Boolean(), nullable=True),
    sa.Column('operating_hours', sa.String(length=50), nullable=True),
    sa.Column('expected_monthly_dispatch', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('expected_monthly_receipts', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('move_in_timeframe', postgresql.ENUM('IMMEDIATE', '1_3_MONTHS', '3_6_MONTHS', '6_12_MONTHS', 'FLEXIBLE', name='moveintimeframe', create_type=False), nullable=True),
    sa.Column('requirement_status', sa.Enum('DRAFT', 'ACTIVE', 'ON_HOLD', 'CLOSED', 'CANCELLED', name='requirementstatus'), nullable=False),
    sa.Column('ai_match_score', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('requirement_score', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('priority_score', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('confidence_score', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_requirements_id'), 'requirements', ['id'], unique=False)
    op.create_index(op.f('ix_requirements_lead_id'), 'requirements', ['lead_id'], unique=False)
    op.create_index(op.f('ix_requirements_requirement_status'), 'requirements', ['requirement_status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_requirements_requirement_status'), table_name='requirements')
    op.drop_index(op.f('ix_requirements_lead_id'), table_name='requirements')
    op.drop_index(op.f('ix_requirements_id'), table_name='requirements')
    op.drop_table('requirements')