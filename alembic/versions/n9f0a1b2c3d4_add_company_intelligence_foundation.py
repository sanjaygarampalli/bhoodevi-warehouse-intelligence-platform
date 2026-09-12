"""Add Company Intelligence & Lead Discovery Foundation."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "n9f0a1b2c3d4"
down_revision = "m8e9f0a1b2c3"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    enums = {
        "warehousedependency": ["VERY_HIGH","HIGH","MEDIUM","LOW","UNKNOWN"], "estimateconfidence": ["LOW","MEDIUM","HIGH"],
        "warehouseusecase": ["STORAGE","DISTRIBUTION","FULFILLMENT","LAST_MILE","REGIONAL_DISTRIBUTION","MANUFACTURING_SUPPORT","RAW_MATERIAL_STORAGE","FINISHED_GOODS_STORAGE","COLD_STORAGE","BONDED_WAREHOUSE","OTHER"],
        "contactdepartment": ["LOGISTICS","SUPPLY_CHAIN","WAREHOUSE","OPERATIONS","PROCUREMENT","FACILITY","REAL_ESTATE","EXPANSION","BUSINESS_DEVELOPMENT","FINANCE","MANAGEMENT","OTHER"],
        "contactseniority": ["OWNER","FOUNDER","C_LEVEL","VP","DIRECTOR","HEAD","MANAGER","SENIOR_MANAGER","EXECUTIVE","OTHER","UNKNOWN"], "contactmethodtype": ["EMAIL","PHONE","LINKEDIN","WEBSITE","OTHER"], "verificationstatus": ["UNVERIFIED","LIKELY_VALID","VERIFIED","INVALID","UNKNOWN"], "icpclassification": ["POOR","LOW","MODERATE","GOOD","EXCELLENT"], "opportunitypriority": ["CRITICAL","HIGH","MEDIUM","LOW"], "nextbestactiontype": ["FIND_DECISION_MAKER","VERIFY_CONTACT_DETAILS","RESEARCH_COMPANY","MONITOR_EXPANSION","CONTACT_IMMEDIATELY","REQUEST_REQUIREMENT_DETAILS","CREATE_LEAD","NO_ACTION"]}
    if bind.dialect.name == "postgresql":
        for name, values in enums.items(): postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)
    def typ(name): return postgresql.ENUM(*enums[name], name=name, create_type=False) if bind.dialect.name == "postgresql" else sa.String(40)
    js = sa.JSON()
    op.create_table("company_intelligence_profiles", sa.Column("id",sa.Integer,primary_key=True),sa.Column("organization_id",sa.Integer,sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("company_id",sa.Integer,sa.ForeignKey("companies.id",ondelete="CASCADE"),nullable=False),sa.Column("industry",sa.String(150)),sa.Column("sub_industry",sa.String(150)),sa.Column("business_model",sa.String(50)),sa.Column("employee_count_min",sa.Integer),sa.Column("employee_count_max",sa.Integer),sa.Column("annual_revenue_min",sa.Numeric(18,2)),sa.Column("annual_revenue_max",sa.Numeric(18,2)),sa.Column("currency",sa.String(3)),sa.Column("headquarters_city",sa.String(100)),sa.Column("headquarters_state",sa.String(100)),sa.Column("headquarters_country",sa.String(100)),sa.Column("operational_geography",js),*[sa.Column(x,sa.Boolean,nullable=False,server_default=sa.false()) for x in ("is_expanding","is_hiring","is_entering_new_market","is_raising_capacity","is_launching_new_product","is_opening_new_facility")],sa.Column("indicator_evidence",js),sa.Column("created_at",sa.DateTime,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime,server_default=sa.func.now()),sa.UniqueConstraint("organization_id","company_id",name="uq_company_intelligence_profile_org_company"))
    op.create_table("company_warehouse_profiles",sa.Column("id",sa.Integer,primary_key=True),sa.Column("organization_id",sa.Integer,sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("company_id",sa.Integer,sa.ForeignKey("companies.id",ondelete="CASCADE"),nullable=False),sa.Column("warehouse_dependency",typ("warehousedependency"),nullable=False),sa.Column("estimated_area_min_sqft",sa.Numeric(14,2)),sa.Column("estimated_area_max_sqft",sa.Numeric(14,2)),sa.Column("estimate_confidence",typ("estimateconfidence"),nullable=False),sa.Column("warehouse_requirement_notes",sa.Text),sa.Column("created_at",sa.DateTime,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime,server_default=sa.func.now()),sa.UniqueConstraint("organization_id","company_id",name="uq_company_warehouse_profile_org_company"))
    op.create_table("company_warehouse_use_cases",sa.Column("id",sa.Integer,primary_key=True),sa.Column("warehouse_profile_id",sa.Integer,sa.ForeignKey("company_warehouse_profiles.id",ondelete="CASCADE"),nullable=False),sa.Column("use_case",typ("warehouseusecase"),nullable=False),sa.UniqueConstraint("warehouse_profile_id","use_case",name="uq_company_warehouse_use_case"))
    op.create_table("company_contacts",sa.Column("id",sa.Integer,primary_key=True),sa.Column("organization_id",sa.Integer,sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("company_id",sa.Integer,sa.ForeignKey("companies.id",ondelete="CASCADE"),nullable=False),sa.Column("first_name",sa.String(100)),sa.Column("last_name",sa.String(100)),sa.Column("full_name",sa.String(255)),sa.Column("job_title",sa.String(255)),sa.Column("department",typ("contactdepartment"),nullable=False),sa.Column("seniority",typ("contactseniority"),nullable=False),sa.Column("is_primary",sa.Boolean,nullable=False,server_default=sa.false()),sa.Column("contact_quality_score",sa.Integer,nullable=False,server_default="0"),sa.Column("contact_quality_explanation",js,nullable=False,server_default="{}"),sa.Column("created_at",sa.DateTime,server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime,server_default=sa.func.now()))
    op.create_table("company_contact_methods",sa.Column("id",sa.Integer,primary_key=True),sa.Column("contact_id",sa.Integer,sa.ForeignKey("company_contacts.id",ondelete="CASCADE"),nullable=False),sa.Column("method_type",typ("contactmethodtype"),nullable=False),sa.Column("value",sa.String(2048),nullable=False),sa.Column("normalized_value",sa.String(2048),nullable=False),sa.Column("is_primary",sa.Boolean,nullable=False,server_default=sa.false()),sa.Column("is_verified",sa.Boolean,nullable=False,server_default=sa.false()),sa.Column("verification_status",typ("verificationstatus"),nullable=False),sa.Column("verification_source",sa.String(255)),sa.Column("verified_at",sa.DateTime),sa.UniqueConstraint("contact_id","method_type","normalized_value",name="uq_company_contact_method"))
    op.create_table("company_icp_assessments",sa.Column("id",sa.Integer,primary_key=True),sa.Column("organization_id",sa.Integer,sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("company_id",sa.Integer,sa.ForeignKey("companies.id",ondelete="CASCADE"),nullable=False),sa.Column("score",sa.Integer,nullable=False),sa.Column("classification",typ("icpclassification"),nullable=False),sa.Column("factors",js,nullable=False),sa.Column("calculated_at",sa.DateTime,server_default=sa.func.now()),sa.UniqueConstraint("organization_id","company_id",name="uq_company_icp_assessments"))
    op.create_table("company_opportunity_assessments",sa.Column("id",sa.Integer,primary_key=True),sa.Column("organization_id",sa.Integer,sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("company_id",sa.Integer,sa.ForeignKey("companies.id",ondelete="CASCADE"),nullable=False),sa.Column("overall_score",sa.Integer,nullable=False),sa.Column("priority",typ("opportunitypriority"),nullable=False),sa.Column("warehouse_fit_score",sa.Integer,nullable=False),sa.Column("demand_score",sa.Integer,nullable=False),sa.Column("geographic_score",sa.Integer,nullable=False),sa.Column("contact_score",sa.Integer,nullable=False),sa.Column("explanation",js,nullable=False),sa.Column("calculated_at",sa.DateTime,server_default=sa.func.now()),sa.UniqueConstraint("organization_id","company_id",name="uq_company_opportunity_assessments"))
    op.create_table("company_next_best_actions",sa.Column("id",sa.Integer,primary_key=True),sa.Column("organization_id",sa.Integer,sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("company_id",sa.Integer,sa.ForeignKey("companies.id",ondelete="CASCADE"),nullable=False),sa.Column("action",typ("nextbestactiontype"),nullable=False),sa.Column("reason",sa.Text,nullable=False),sa.Column("calculated_at",sa.DateTime,server_default=sa.func.now()),sa.UniqueConstraint("organization_id","company_id",name="uq_company_next_best_action"))
    if bind.dialect.name == "postgresql":
        op.create_check_constraint("ck_ci_employee_range", "company_intelligence_profiles", "employee_count_min IS NULL OR employee_count_max IS NULL OR employee_count_min <= employee_count_max")
        op.create_check_constraint("ck_ci_revenue_range", "company_intelligence_profiles", "annual_revenue_min IS NULL OR annual_revenue_max IS NULL OR annual_revenue_min <= annual_revenue_max")
        op.create_check_constraint("ck_cw_area_range", "company_warehouse_profiles", "estimated_area_min_sqft IS NULL OR estimated_area_max_sqft IS NULL OR estimated_area_min_sqft <= estimated_area_max_sqft")
        op.create_check_constraint("ck_company_icp_score", "company_icp_assessments", "score >= 0 AND score <= 100")
        op.create_check_constraint("ck_company_opportunity_score", "company_opportunity_assessments", "overall_score >= 0 AND overall_score <= 100")
        op.create_check_constraint("ck_company_opportunity_warehouse_fit", "company_opportunity_assessments", "warehouse_fit_score >= 0 AND warehouse_fit_score <= 100")
        op.create_check_constraint("ck_company_opportunity_demand", "company_opportunity_assessments", "demand_score >= 0 AND demand_score <= 100")
        op.create_check_constraint("ck_company_opportunity_geography", "company_opportunity_assessments", "geographic_score >= 0 AND geographic_score <= 100")
        op.create_check_constraint("ck_company_opportunity_contact", "company_opportunity_assessments", "contact_score >= 0 AND contact_score <= 100")
    for index_name, table_name, columns in (
        ("ix_ci_profiles_org", "company_intelligence_profiles", ["organization_id"]),
        ("ix_cw_profiles_org", "company_warehouse_profiles", ["organization_id"]),
        ("ix_company_contacts_org_company", "company_contacts", ["organization_id", "company_id"]),
        ("uq_company_contact_methods_primary", "company_contact_methods", ["contact_id"]),
        ("ix_company_icp_assessments_org_company", "company_icp_assessments", ["organization_id", "company_id"]),
        ("ix_company_opportunity_assessments_org_company", "company_opportunity_assessments", ["organization_id", "company_id"]),
        ("ix_company_next_best_actions_org_company", "company_next_best_actions", ["organization_id", "company_id"]),
    ):
        kwargs = {}
        if index_name == "uq_company_contact_methods_primary":
            kwargs = {"unique": True, "postgresql_where": sa.text("is_primary = true"), "sqlite_where": sa.text("is_primary = 1")}
        op.create_index(index_name, table_name, columns, **kwargs)

def downgrade():
    for table in ("company_next_best_actions","company_opportunity_assessments","company_icp_assessments","company_contact_methods","company_contacts","company_warehouse_use_cases","company_warehouse_profiles","company_intelligence_profiles"): op.drop_table(table)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum_name in ("nextbestactiontype", "opportunitypriority", "icpclassification", "verificationstatus", "contactmethodtype", "contactseniority", "contactdepartment", "warehouseusecase", "estimateconfidence", "warehousedependency"):
            sa.Enum(name=enum_name).drop(bind, checkfirst=True)