"""Align intelligence JSON storage with the existing PostgreSQL JSONB models.

Revision ID: v7a8b9c0d1e2
Revises: u6f7a8b9c0d1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "v7a8b9c0d1e2"
down_revision = "u6f7a8b9c0d1"
branch_labels = None
depends_on = None

COLUMNS = {
    "company_contacts": ("contact_quality_explanation",),
    "company_icp_assessments": ("factors",),
    "company_intelligence_profiles": ("operational_geography", "indicator_evidence"),
    "company_opportunity_assessments": ("explanation",),
    "company_warehouse_requirement_profiles": ("requirements",),
    "f5_assessments": ("dimensions", "reasons", "confidence_reasons"),
    "f5_company_profiles": ("aliases",),
    "f5_evidence_claims": ("confidence_reasons",),
    "response_qualification_assessments": ("observed_facts", "uncertainty", "warehouse_details"),
    "warehouse_capability_profiles": ("capabilities",),
}


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table, columns in COLUMNS.items():
            for column in columns:
                op.alter_column(table, column, existing_type=sa.JSON(), type_=postgresql.JSONB(),
                                postgresql_using=f'"{column}"::jsonb')


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table, columns in COLUMNS.items():
            for column in columns:
                op.alter_column(table, column, existing_type=postgresql.JSONB(), type_=sa.JSON(),
                                postgresql_using=f'"{column}"::json')
