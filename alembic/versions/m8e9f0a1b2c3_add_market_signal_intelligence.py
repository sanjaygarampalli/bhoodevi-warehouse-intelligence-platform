"""Add market signal intelligence foundation.

Revision ID: m8e9f0a1b2c3
Revises: l7d8e9f0a1b2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "m8e9f0a1b2c3"
down_revision = "l7d8e9f0a1b2"
branch_labels = None
depends_on = None


def _enum(*values, name):
    return postgresql.ENUM(*values, name=name)


def _column_enum(enum_type):
    return postgresql.ENUM(
        *enum_type.enums,
        name=enum_type.name,
        create_type=False,
    )


def upgrade():
    market_signal_type = _enum("COMPANY_EXPANSION", "MANUFACTURING_EXPANSION", "LOGISTICS_EXPANSION", "DISTRIBUTION_EXPANSION", "ECOMMERCE_EXPANSION", "NEW_FACILITY", "NEW_WAREHOUSE", "NEW_DISTRIBUTION_CENTER", "MARKET_ENTRY", "CAPACITY_EXPANSION", "INDUSTRIAL_INVESTMENT", "LAND_ACQUISITION", "GOVERNMENT_TENDER", "OTHER", name="marketsignaltype")
    market_signal_status = _enum("DETECTED", "UNDER_REVIEW", "VERIFIED", "REJECTED", "ARCHIVED", name="marketsignalstatus")
    source_type = _enum("COMPANY_ANNOUNCEMENT", "GOVERNMENT_ANNOUNCEMENT", "NEWS", "INDUSTRY_REPORT", "TENDER_PORTAL", "COMPANY_WEBSITE", "MANUAL_RESEARCH", "OTHER", name="marketsignalsourcetype")
    confidence = _enum("LOW", "MEDIUM", "HIGH", name="marketsignalconfidence")
    evidence_source_type = _enum("COMPANY_ANNOUNCEMENT", "GOVERNMENT_ANNOUNCEMENT", "NEWS", "INDUSTRY_REPORT", "TENDER_PORTAL", "COMPANY_WEBSITE", "MANUAL_RESEARCH", "OTHER", name="evidencesourcetype")
    credibility = _enum("PRIMARY", "HIGH", "MEDIUM", "LOW", name="evidencecredibility")
    candidate_status = _enum("CANDIDATE", "UNDER_REVIEW", "ACCEPTED", "REJECTED", "CONVERTED", name="requirementcandidatestatus")
    demand_strength = _enum("STRONG", "MODERATE", "POSSIBLE", "WEAK", "NONE", name="demandstrength")
    candidate_confidence = _enum("LOW", "MEDIUM", "HIGH", name="candidateconfidence")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for item in (market_signal_type, market_signal_status, source_type, confidence, evidence_source_type, credibility, candidate_status, demand_strength, candidate_confidence):
            item.create(bind, checkfirst=True)
    op.create_table(
        "market_signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("signal_type", _column_enum(market_signal_type), nullable=False),
        sa.Column("status", _column_enum(market_signal_status), nullable=False, server_default="DETECTED"),
        sa.Column("source_type", _column_enum(source_type), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("source_published_at", sa.DateTime(), nullable=True),
        sa.Column("detected_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("location_text", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("announced_investment_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("announced_investment_currency", sa.String(3), nullable=True),
        sa.Column("confidence_level", _column_enum(confidence), nullable=False, server_default="LOW"),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_market_signals__organization__status", "market_signals", ["organization_id", "status"])
    op.create_index("ix_market_signals__organization__company", "market_signals", ["organization_id", "company_id"])
    op.create_index("ix_market_signals__organization__type", "market_signals", ["organization_id", "signal_type"])
    op.create_table(
        "market_signal_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_signal_id", sa.Integer(), sa.ForeignKey("market_signals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", _column_enum(evidence_source_type), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("credibility_level", _column_enum(credibility), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_market_signal_evidence__signal", "market_signal_evidence", ["market_signal_id"])
    op.create_table(
        "requirement_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("market_signal_id", sa.Integer(), sa.ForeignKey("market_signals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", _column_enum(candidate_status), nullable=False, server_default="CANDIDATE"),
        sa.Column("demand_strength", _column_enum(demand_strength), nullable=False),
        sa.Column("confidence_level", _column_enum(candidate_confidence), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("district", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("market_signal_id", name="uq_requirement_candidates__market_signal"),
    )
    op.create_index("ix_requirement_candidates__organization__status", "requirement_candidates", ["organization_id", "status"])
    op.create_index("ix_requirement_candidates__organization__company", "requirement_candidates", ["organization_id", "company_id"])


def downgrade():
    op.drop_table("requirement_candidates")
    op.drop_table("market_signal_evidence")
    op.drop_table("market_signals")
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for name in ("candidateconfidence", "demandstrength", "requirementcandidatestatus", "evidencecredibility", "evidencesourcetype", "marketsignalconfidence", "marketsignalsourcetype", "marketsignalstatus", "marketsignaltype"):
            postgresql.ENUM(name=name).drop(bind, checkfirst=True)