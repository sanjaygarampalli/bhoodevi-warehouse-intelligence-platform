"""Add additive F5 company and ICP intelligence compatibility layer."""
from alembic import op
import sqlalchemy as sa

revision = "s4e5f6a7b8c9"
down_revision = "r3d4e5f6a7b8"
branch_labels = None
depends_on = None


def _enum(name, values):
    """Use pre-created PostgreSQL enums so repeated table references are safe."""
    return sa.dialects.postgresql.ENUM(*values, name=name, create_type=False)


def upgrade():
    classification = ["FACT", "INFERENCE", "UNKNOWN"]
    freshness = ["FRESH", "AGING", "STALE", "UNKNOWN"]
    lifecycle = ["DISCOVERED", "IDENTIFIED", "ENRICHED", "REGIONALLY_RELEVANT", "ICP_EVALUATED", "QUALIFIED_FOR_REQUIREMENT_RESEARCH", "DISQUALIFIED", "DUPLICATE", "ARCHIVED"]
    duplicate = ["NONE", "POSSIBLE_DUPLICATE", "CONFIRMED_DUPLICATE", "UNRELATED"]
    presence = ["OFFICE", "FACTORY", "WAREHOUSE", "DISTRIBUTION_CENTER", "RETAIL_NETWORK", "DEALER_NETWORK", "PROJECT", "EXPANSION", "LOGISTICS_ACTIVITY", "OTHER"]
    suitability = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    bind = op.get_bind()
    for name, values in (
        ("f5lifecyclestatus", lifecycle),
        ("f5duplicatestatus", duplicate),
        ("f5presencetype", presence),
        ("f5classification", classification),
        ("f5freshness", freshness),
        ("f5claimclassification", classification),
        ("f5claimfreshness", freshness),
        ("f5industryclassification", classification),
        ("f5warehousesuitability", suitability),
        ("f5assessmentfreshness", freshness),
    ):
        sa.dialects.postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)
    op.create_table("f5_company_profiles",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False), sa.Column("normalized_domain", sa.String(255)), sa.Column("registration_identifier", sa.String(150)), sa.Column("source_identifier", sa.String(255)), sa.Column("aliases", sa.JSON(), nullable=False), sa.Column("lifecycle_status", _enum("f5lifecyclestatus", lifecycle), nullable=False, server_default="DISCOVERED"), sa.Column("duplicate_status", _enum("f5duplicatestatus", duplicate), nullable=False, server_default="NONE"), sa.Column("source", sa.String(255)), sa.Column("last_verified_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "company_id", name="uq_f5_company_profiles_org_company"))
    op.create_index("ix_f5_company_profiles_org_status", "f5_company_profiles", ["organization_id", "lifecycle_status"])
    op.create_index("ix_f5_company_profiles_org_normalized_name", "f5_company_profiles", ["organization_id", "normalized_name"])
    op.create_table("f5_regional_presence",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("profile_id", sa.Integer(), sa.ForeignKey("f5_company_profiles.id", ondelete="CASCADE"), nullable=False), sa.Column("presence_type", _enum("f5presencetype", presence), nullable=False), sa.Column("region", sa.String(150), nullable=False), sa.Column("city", sa.String(100)), sa.Column("district", sa.String(100)), sa.Column("state", sa.String(100)), sa.Column("country", sa.String(100), server_default="India"), sa.Column("classification", _enum("f5classification", classification), nullable=False), sa.Column("confidence", sa.Float()), sa.Column("observed_at", sa.DateTime()), sa.Column("last_verified_at", sa.DateTime()), sa.Column("freshness", _enum("f5freshness", freshness), nullable=False, server_default="UNKNOWN"), sa.Column("source", sa.String(255)), sa.Column("source_url", sa.String(2048)), sa.Column("notes", sa.Text()))
    op.create_index("ix_f5_presence_profile_region", "f5_regional_presence", ["profile_id", "region"])
    op.create_table("f5_evidence_claims",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("profile_id", sa.Integer(), sa.ForeignKey("f5_company_profiles.id", ondelete="CASCADE"), nullable=False), sa.Column("claim", sa.Text(), nullable=False), sa.Column("claim_type", sa.String(100), nullable=False), sa.Column("classification", _enum("f5claimclassification", classification), nullable=False), sa.Column("source", sa.String(255)), sa.Column("source_url", sa.String(2048)), sa.Column("source_title", sa.String(500)), sa.Column("published_at", sa.DateTime()), sa.Column("observed_at", sa.DateTime()), sa.Column("last_verified_at", sa.DateTime()), sa.Column("freshness", _enum("f5claimfreshness", freshness), nullable=False, server_default="UNKNOWN"), sa.Column("credibility", sa.String(30)), sa.Column("confidence", sa.Float()), sa.Column("confidence_reasons", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_f5_claims_profile_type", "f5_evidence_claims", ["profile_id", "claim_type"])
    op.create_table("f5_assessments",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False), sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False), sa.Column("industry_classification", _enum("f5industryclassification", classification), nullable=False, server_default="UNKNOWN"), sa.Column("industry", sa.String(150)), sa.Column("warehouse_suitability", _enum("f5warehousesuitability", suitability), nullable=False, server_default="UNKNOWN"), sa.Column("icp_classification", sa.String(30), nullable=False, server_default="UNKNOWN"), sa.Column("dimensions", sa.JSON(), nullable=False), sa.Column("reasons", sa.JSON(), nullable=False), sa.Column("confidence", sa.Float()), sa.Column("confidence_reasons", sa.JSON(), nullable=False), sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("freshness", _enum("f5assessmentfreshness", freshness), nullable=False, server_default="UNKNOWN"), sa.Column("calculated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("organization_id", "company_id", name="uq_f5_assessments_org_company"), sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_f5_assessment_confidence"))


def downgrade():
    op.drop_table("f5_assessments")
    op.drop_index("ix_f5_claims_profile_type", table_name="f5_evidence_claims")
    op.drop_table("f5_evidence_claims")
    op.drop_index("ix_f5_presence_profile_region", table_name="f5_regional_presence")
    op.drop_table("f5_regional_presence")
    op.drop_index("ix_f5_company_profiles_org_normalized_name", table_name="f5_company_profiles")
    op.drop_index("ix_f5_company_profiles_org_status", table_name="f5_company_profiles")
    op.drop_table("f5_company_profiles")
    bind = op.get_bind()
    for name in (
        "f5assessmentfreshness",
        "f5warehousesuitability",
        "f5industryclassification",
        "f5claimfreshness",
        "f5claimclassification",
        "f5freshness",
        "f5classification",
        "f5presencetype",
        "f5duplicatestatus",
        "f5lifecyclestatus",
    ):
        sa.dialects.postgresql.ENUM(name=name).drop(bind, checkfirst=True)