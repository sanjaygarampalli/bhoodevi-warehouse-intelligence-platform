"""Add requirement-specific evidence and explainable assessment."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "t5e6f7a8b9c0"
down_revision = "s4e5f6a7b8c9"
branch_labels = None
depends_on = None


def _enum(name, values):
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for name, values in (
            ("requirementevidenceclassification", ["FACT", "INFERENCE", "UNKNOWN"]),
            ("requirementevidenceverificationstatus", ["UNVERIFIED", "REVIEWED", "VERIFIED", "REJECTED"]),
            ("requirementfreshness", ["FRESH", "AGING", "STALE", "UNKNOWN"]),
        ):
            postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    evidence_classification = _enum("requirementevidenceclassification", ["FACT", "INFERENCE", "UNKNOWN"])
    verification_status = _enum("requirementevidenceverificationstatus", ["UNVERIFIED", "REVIEWED", "VERIFIED", "REJECTED"])
    freshness = _enum("requirementfreshness", ["FRESH", "AGING", "STALE", "UNKNOWN"])
    op.create_table(
        "requirement_intelligence_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(100)),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("observed_evidence", sa.Text(), nullable=False),
        sa.Column("inference", sa.Text()),
        sa.Column("classification", evidence_classification, nullable=False),
        sa.Column("evidence_date", sa.DateTime()),
        sa.Column("verification_status", verification_status, nullable=False, server_default="UNVERIFIED"),
        sa.Column("verified_at", sa.DateTime()),
        sa.Column("verified_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("confidence", sa.Numeric(5, 2)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_requirement_intelligence_evidence__requirement", "requirement_intelligence_evidence", ["requirement_id"])
    op.create_index("ix_requirement_intelligence_evidence__organization", "requirement_intelligence_evidence", ["organization_id"])
    op.create_table(
        "requirement_intelligence_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", sa.Integer(), sa.ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, unique=True),
        *[sa.Column(name, sa.Numeric(5, 2)) for name in ("requirement_confidence", "geography_confidence", "size_confidence", "timing_confidence", "operational_confidence", "commercial_confidence", "evidence_strength")],
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("freshness", freshness, nullable=False, server_default="UNKNOWN"),
        sa.Column("freshness_anchor", sa.DateTime()),
        sa.Column("calculated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_requirement_intelligence_assessments__organization", "requirement_intelligence_assessments", ["organization_id"])


def downgrade():
    op.drop_index("ix_requirement_intelligence_assessments__organization", table_name="requirement_intelligence_assessments")
    op.drop_table("requirement_intelligence_assessments")
    op.drop_index("ix_requirement_intelligence_evidence__organization", table_name="requirement_intelligence_evidence")
    op.drop_index("ix_requirement_intelligence_evidence__requirement", table_name="requirement_intelligence_evidence")
    op.drop_table("requirement_intelligence_evidence")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for name in ("requirementfreshness", "requirementevidenceverificationstatus", "requirementevidenceclassification"):
            postgresql.ENUM(name=name).drop(bind, checkfirst=True)