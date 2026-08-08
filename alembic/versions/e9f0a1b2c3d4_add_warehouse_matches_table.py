"""add warehouse_matches table

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-08-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e9f0a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'd8e9f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- Warehouse enrichment fields (PART A) ---

    # `warehousetype` was already created by the `requirements` migration
    # (d8e9f0a1b2c3) with values COVERED/OPEN_YARD/COLD_STORAGE/BONDED/
    # MULTIPURPOSE/CONTAINER/TRANSIT/OTHER.  warehouses.warehouse_type
    # reuses that same `WarehouseType` enum, so reference the existing
    # PostgreSQL type instead of recreating it.
    op.add_column('warehouses', sa.Column('warehouse_code', sa.String(length=50), nullable=True))
    op.add_column('warehouses', sa.Column('warehouse_type', postgresql.ENUM('COVERED', 'OPEN_YARD', 'COLD_STORAGE', 'BONDED', 'MULTIPURPOSE', 'CONTAINER', 'TRANSIT', 'OTHER', name='warehousetype', create_type=False), nullable=True))
    op.add_column('warehouses', sa.Column('total_area_sqft', sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column('warehouses', sa.Column('built_up_area_sqft', sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column('warehouses', sa.Column('open_area_sqft', sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column('warehouses', sa.Column('height_ft', sa.Numeric(precision=8, scale=2), nullable=True))
    op.add_column('warehouses', sa.Column('floor_load_kg_sqm', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('warehouses', sa.Column('address_line1', sa.String(length=255), nullable=True))
    op.add_column('warehouses', sa.Column('address_line2', sa.String(length=255), nullable=True))
    op.add_column('warehouses', sa.Column('country', sa.String(length=100), nullable=True))
    op.add_column('warehouses', sa.Column('postal_code', sa.String(length=10), nullable=True))
    op.add_column('warehouses', sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True))
    op.add_column('warehouses', sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True))
    op.add_column('warehouses', sa.Column('rent_per_month', sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column('warehouses', sa.Column('currency', sa.String(length=3), nullable=True))
    op.add_column('warehouses', sa.Column('min_lease_months', sa.Integer(), nullable=True))
    op.add_column('warehouses', sa.Column('available_from', sa.DateTime(), nullable=True))

    # PostgreSQL requires the enum type to exist before a column can use it.
    # Explicitly create `availabilitystatus` before adding the column.
    availability_status = postgresql.ENUM(
        'AVAILABLE', 'PARTIALLY_OCCUPIED', 'OCCUPIED', 'UNDER_MAINTENANCE', 'INACTIVE',
        name='availabilitystatus',
        create_type=False,
    )
    availability_status.create(op.get_bind(), checkfirst=True)
    op.add_column('warehouses', sa.Column('availability_status', availability_status, nullable=True))

    op.add_column('warehouses', sa.Column('amenities', sa.String(length=500), nullable=True))
    op.add_column('warehouses', sa.Column('certifications', sa.String(length=500), nullable=True))
    op.add_column('warehouses', sa.Column('condition_grade', sa.String(length=1), nullable=True))
    op.add_column('warehouses', sa.Column('occupancy_rate', sa.Numeric(precision=5, scale=2), nullable=True))
    op.create_index(op.f('ix_warehouses_warehouse_code'), 'warehouses', ['warehouse_code'], unique=True)
    op.create_index(op.f('ix_warehouses_warehouse_type'), 'warehouses', ['warehouse_type'], unique=False)
    op.create_index(op.f('ix_warehouses_owner_id'), 'warehouses', ['owner_id'], unique=False)

    # New enum types for the warehouse_matches table.
    warehouse_match_status = postgresql.ENUM(
        'AI_RECOMMENDED', 'SHORTLISTED', 'PROPOSED', 'LEAD_CHOSEN', 'REJECTED', 'CONVERTED', 'STALE',
        name='warehousematchstatus',
        create_type=False,
    )
    warehouse_match_status.create(op.get_bind(), checkfirst=True)
    matched_by = postgresql.ENUM(
        'AI', 'MANUAL', 'HYBRID',
        name='matchedby',
        create_type=False,
    )
    matched_by.create(op.get_bind(), checkfirst=True)

    op.create_table('warehouse_matches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('lead_id', sa.Integer(), nullable=False),
    sa.Column('requirement_id', sa.Integer(), nullable=True),
    sa.Column('warehouse_id', sa.Integer(), nullable=False),
    sa.Column('match_score', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('match_rank', sa.Integer(), nullable=True),
    sa.Column('geo_distance_km', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('transit_days', sa.Integer(), nullable=True),
    sa.Column('capacity_fit', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('budget_fit', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('requirement_compatibility', sa.Text(), nullable=True),
    sa.Column('match_reasons', sa.Text(), nullable=True),
    sa.Column('concern_reasons', sa.Text(), nullable=True),
    sa.Column('top_reason', sa.Text(), nullable=True),
    sa.Column('status', warehouse_match_status, nullable=False),
    sa.Column('matched_by', matched_by, nullable=False),
    sa.Column('model_id', sa.String(length=100), nullable=True),
    sa.Column('model_version', sa.String(length=50), nullable=True),
    sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('match_score >= 0 AND match_score <= 100', name='ck_warehouse_matches__match_score_range'),
    sa.CheckConstraint("status IN ('AI_RECOMMENDED','SHORTLISTED','PROPOSED','LEAD_CHOSEN','REJECTED','CONVERTED','STALE')", name='ck_warehouse_matches__status'),
    sa.CheckConstraint("matched_by IN ('AI','MANUAL','HYBRID')", name='ck_warehouse_matches__matched_by'),
    sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_warehouse_matches_id'), 'warehouse_matches', ['id'], unique=False)
    op.create_index(op.f('ix_warehouse_matches_lead_id'), 'warehouse_matches', ['lead_id'], unique=False)
    op.create_index(op.f('ix_warehouse_matches_requirement_id'), 'warehouse_matches', ['requirement_id'], unique=False)
    op.create_index(op.f('ix_warehouse_matches_reviewed_by_user_id'), 'warehouse_matches', ['reviewed_by_user_id'], unique=False)
    op.create_index(op.f('ix_warehouse_matches_status'), 'warehouse_matches', ['status'], unique=False)
    op.create_index(op.f('ix_warehouse_matches_warehouse_id'), 'warehouse_matches', ['warehouse_id'], unique=False)
    op.create_index('ix_warehouse_matches__requirement_id__match_score', 'warehouse_matches', ['requirement_id', 'match_score'], unique=False)
    op.create_index('ix_warehouse_matches__lead_id__match_score', 'warehouse_matches', ['lead_id', 'match_score'], unique=False)
    op.create_index('ix_warehouse_matches__warehouse_id__status', 'warehouse_matches', ['warehouse_id', 'status'], unique=False)

    # Partial unique indexes: enforce one lead-level match per (lead_id, warehouse_id)
    # and one requirement-level match per (requirement_id, warehouse_id).
    op.create_index(
        'uq_warehouse_matches__lead__warehouse__partial',
        'warehouse_matches',
        ['lead_id', 'warehouse_id'],
        unique=True,
        sqlite_where=sa.text('requirement_id IS NULL'),
        postgresql_where=sa.text('requirement_id IS NULL'),
    )
    op.create_index(
        'uq_warehouse_matches__requirement__warehouse__partial',
        'warehouse_matches',
        ['requirement_id', 'warehouse_id'],
        unique=True,
        sqlite_where=sa.text('requirement_id IS NOT NULL'),
        postgresql_where=sa.text('requirement_id IS NOT NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_warehouses_owner_id'), table_name='warehouses')
    op.drop_index(op.f('ix_warehouses_warehouse_type'), table_name='warehouses')
    op.drop_index(op.f('ix_warehouses_warehouse_code'), table_name='warehouses')
    op.drop_column('warehouses', 'occupancy_rate')
    op.drop_column('warehouses', 'condition_grade')
    op.drop_column('warehouses', 'certifications')
    op.drop_column('warehouses', 'amenities')
    op.drop_column('warehouses', 'availability_status')
    op.drop_column('warehouses', 'available_from')
    op.drop_column('warehouses', 'min_lease_months')
    op.drop_column('warehouses', 'currency')
    op.drop_column('warehouses', 'rent_per_month')
    op.drop_column('warehouses', 'longitude')
    op.drop_column('warehouses', 'latitude')
    op.drop_column('warehouses', 'postal_code')
    op.drop_column('warehouses', 'country')
    op.drop_column('warehouses', 'address_line2')
    op.drop_column('warehouses', 'address_line1')
    op.drop_column('warehouses', 'floor_load_kg_sqm')
    op.drop_column('warehouses', 'height_ft')
    op.drop_column('warehouses', 'open_area_sqft')
    op.drop_column('warehouses', 'built_up_area_sqft')
    op.drop_column('warehouses', 'total_area_sqft')
    op.drop_column('warehouses', 'warehouse_type')
    op.drop_column('warehouses', 'warehouse_code')

    op.drop_index('uq_warehouse_matches__requirement__warehouse__partial', table_name='warehouse_matches')
    op.drop_index('uq_warehouse_matches__lead__warehouse__partial', table_name='warehouse_matches')
    op.drop_index('ix_warehouse_matches__warehouse_id__status', table_name='warehouse_matches')
    op.drop_index('ix_warehouse_matches__lead_id__match_score', table_name='warehouse_matches')
    op.drop_index('ix_warehouse_matches__requirement_id__match_score', table_name='warehouse_matches')
    op.drop_index(op.f('ix_warehouse_matches_warehouse_id'), table_name='warehouse_matches')
    op.drop_index(op.f('ix_warehouse_matches_status'), table_name='warehouse_matches')
    op.drop_index(op.f('ix_warehouse_matches_reviewed_by_user_id'), table_name='warehouse_matches')
    op.drop_index(op.f('ix_warehouse_matches_requirement_id'), table_name='warehouse_matches')
    op.drop_index(op.f('ix_warehouse_matches_lead_id'), table_name='warehouse_matches')
    op.drop_index(op.f('ix_warehouse_matches_id'), table_name='warehouse_matches')
    op.drop_table('warehouse_matches')

    # Drop the enum types created by this migration after their columns
    # (and the warehouse_matches table) have been removed.
    # `warehousetype` is NOT dropped here — it is owned by the earlier
    # `requirements` migration and is still used by requirements.warehouse_type.
    availability_status = postgresql.ENUM(
        'AVAILABLE', 'PARTIALLY_OCCUPIED', 'OCCUPIED', 'UNDER_MAINTENANCE', 'INACTIVE',
        name='availabilitystatus',
        create_type=False,
    )
    availability_status.drop(op.get_bind(), checkfirst=True)
    warehouse_match_status = postgresql.ENUM(
        'AI_RECOMMENDED', 'SHORTLISTED', 'PROPOSED', 'LEAD_CHOSEN', 'REJECTED', 'CONVERTED', 'STALE',
        name='warehousematchstatus',
        create_type=False,
    )
    warehouse_match_status.drop(op.get_bind(), checkfirst=True)
    matched_by = postgresql.ENUM(
        'AI', 'MANUAL', 'HYBRID',
        name='matchedby',
        create_type=False,
    )
    matched_by.drop(op.get_bind(), checkfirst=True)