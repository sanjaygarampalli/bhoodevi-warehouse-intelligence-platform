import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WarehouseDependency(str, enum.Enum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class EstimateConfidence(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ContactDepartment(str, enum.Enum):
    LOGISTICS = "LOGISTICS"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    WAREHOUSE = "WAREHOUSE"
    OPERATIONS = "OPERATIONS"
    PROCUREMENT = "PROCUREMENT"
    FACILITY = "FACILITY"
    REAL_ESTATE = "REAL_ESTATE"
    EXPANSION = "EXPANSION"
    BUSINESS_DEVELOPMENT = "BUSINESS_DEVELOPMENT"
    FINANCE = "FINANCE"
    MANAGEMENT = "MANAGEMENT"
    OTHER = "OTHER"


class ContactSeniority(str, enum.Enum):
    OWNER = "OWNER"
    FOUNDER = "FOUNDER"
    C_LEVEL = "C_LEVEL"
    VP = "VP"
    DIRECTOR = "DIRECTOR"
    HEAD = "HEAD"
    MANAGER = "MANAGER"
    SENIOR_MANAGER = "SENIOR_MANAGER"
    EXECUTIVE = "EXECUTIVE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class ContactMethodType(str, enum.Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    LINKEDIN = "LINKEDIN"
    WEBSITE = "WEBSITE"
    OTHER = "OTHER"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    LIKELY_VALID = "LIKELY_VALID"
    VERIFIED = "VERIFIED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class IcpClassification(str, enum.Enum):
    POOR = "POOR"
    LOW = "LOW"
    MODERATE = "MODERATE"
    GOOD = "GOOD"
    EXCELLENT = "EXCELLENT"


class OpportunityPriority(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NextBestActionType(str, enum.Enum):
    FIND_DECISION_MAKER = "FIND_DECISION_MAKER"
    VERIFY_CONTACT_DETAILS = "VERIFY_CONTACT_DETAILS"
    RESEARCH_COMPANY = "RESEARCH_COMPANY"
    MONITOR_EXPANSION = "MONITOR_EXPANSION"
    CONTACT_IMMEDIATELY = "CONTACT_IMMEDIATELY"
    REQUEST_REQUIREMENT_DETAILS = "REQUEST_REQUIREMENT_DETAILS"
    CREATE_LEAD = "CREATE_LEAD"
    NO_ACTION = "NO_ACTION"


class WarehouseUseCase(str, enum.Enum):
    STORAGE = "STORAGE"
    DISTRIBUTION = "DISTRIBUTION"
    FULFILLMENT = "FULFILLMENT"
    LAST_MILE = "LAST_MILE"
    REGIONAL_DISTRIBUTION = "REGIONAL_DISTRIBUTION"
    MANUFACTURING_SUPPORT = "MANUFACTURING_SUPPORT"
    RAW_MATERIAL_STORAGE = "RAW_MATERIAL_STORAGE"
    FINISHED_GOODS_STORAGE = "FINISHED_GOODS_STORAGE"
    COLD_STORAGE = "COLD_STORAGE"
    BONDED_WAREHOUSE = "BONDED_WAREHOUSE"
    OTHER = "OTHER"


def _json_type():
    return JSON().with_variant(JSONB(), "postgresql")


def _enum_type(enum_class: type[enum.Enum], name: str):
    return Enum(enum_class, name=name, values_callable=lambda values: [value.value for value in values])


class CompanyIntelligenceProfile(Base):
    __tablename__ = "company_intelligence_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "company_id", name="uq_company_intelligence_profile_org_company"),
        CheckConstraint("employee_count_min IS NULL OR employee_count_max IS NULL OR employee_count_min <= employee_count_max", name="ck_ci_employee_range"),
        CheckConstraint("annual_revenue_min IS NULL OR annual_revenue_max IS NULL OR annual_revenue_min <= annual_revenue_max", name="ck_ci_revenue_range"),
        CheckConstraint("employee_count_min IS NULL OR employee_count_min >= 0", name="ck_ci_employee_min"),
        CheckConstraint("employee_count_max IS NULL OR employee_count_max >= 0", name="ck_ci_employee_max"),
        CheckConstraint("annual_revenue_min IS NULL OR annual_revenue_min >= 0", name="ck_ci_revenue_min"),
        CheckConstraint("annual_revenue_max IS NULL OR annual_revenue_max >= 0", name="ck_ci_revenue_max"),
        Index("ix_ci_profiles_org", "organization_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(150))
    sub_industry: Mapped[str | None] = mapped_column(String(150))
    business_model: Mapped[str | None] = mapped_column(String(50))
    employee_count_min: Mapped[int | None] = mapped_column(Integer)
    employee_count_max: Mapped[int | None] = mapped_column(Integer)
    annual_revenue_min: Mapped[float | None] = mapped_column(Numeric(18, 2))
    annual_revenue_max: Mapped[float | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    headquarters_city: Mapped[str | None] = mapped_column(String(100))
    headquarters_state: Mapped[str | None] = mapped_column(String(100))
    headquarters_country: Mapped[str | None] = mapped_column(String(100))
    operational_geography: Mapped[dict[str, Any] | None] = mapped_column(_json_type())
    is_expanding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hiring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_entering_new_market: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_raising_capacity: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_launching_new_product: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_opening_new_facility: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    indicator_evidence: Mapped[dict[str, Any] | None] = mapped_column(_json_type())
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class CompanyWarehouseProfile(Base):
    __tablename__ = "company_warehouse_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "company_id", name="uq_company_warehouse_profile_org_company"),
        CheckConstraint("estimated_area_min_sqft IS NULL OR estimated_area_max_sqft IS NULL OR estimated_area_min_sqft <= estimated_area_max_sqft", name="ck_cw_area_range"),
        CheckConstraint("estimated_area_min_sqft IS NULL OR estimated_area_min_sqft >= 0", name="ck_cw_area_min"),
        CheckConstraint("estimated_area_max_sqft IS NULL OR estimated_area_max_sqft >= 0", name="ck_cw_area_max"),
        Index("ix_cw_profiles_org", "organization_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    warehouse_dependency: Mapped[WarehouseDependency] = mapped_column(_enum_type(WarehouseDependency, "warehousedependency"), nullable=False, default=WarehouseDependency.UNKNOWN)
    estimated_area_min_sqft: Mapped[float | None] = mapped_column(Numeric(14, 2))
    estimated_area_max_sqft: Mapped[float | None] = mapped_column(Numeric(14, 2))
    estimate_confidence: Mapped[EstimateConfidence] = mapped_column(_enum_type(EstimateConfidence, "estimateconfidence"), nullable=False, default=EstimateConfidence.LOW)
    warehouse_requirement_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    use_cases: Mapped[list["CompanyWarehouseUseCase"]] = relationship(cascade="all, delete-orphan")


class CompanyWarehouseUseCase(Base):
    __tablename__ = "company_warehouse_use_cases"
    __table_args__ = (UniqueConstraint("warehouse_profile_id", "use_case", name="uq_company_warehouse_use_case"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    warehouse_profile_id: Mapped[int] = mapped_column(ForeignKey("company_warehouse_profiles.id", ondelete="CASCADE"), nullable=False)
    use_case: Mapped[WarehouseUseCase] = mapped_column(_enum_type(WarehouseUseCase, "warehouseusecase"), nullable=False)


class CompanyContact(Base):
    __tablename__ = "company_contacts"
    __table_args__ = (Index("ix_company_contacts_org_company", "organization_id", "company_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    full_name: Mapped[str | None] = mapped_column(String(255))
    job_title: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[ContactDepartment] = mapped_column(_enum_type(ContactDepartment, "contactdepartment"), nullable=False)
    seniority: Mapped[ContactSeniority] = mapped_column(_enum_type(ContactSeniority, "contactseniority"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contact_quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contact_quality_explanation: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    methods: Mapped[list["CompanyContactMethod"]] = relationship(cascade="all, delete-orphan")


class CompanyContactMethod(Base):
    __tablename__ = "company_contact_methods"
    __table_args__ = (
        UniqueConstraint("contact_id", "method_type", "normalized_value", name="uq_company_contact_method"),
        Index(
            "uq_company_contact_methods_primary",
            "contact_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
            sqlite_where=text("is_primary = 1"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("company_contacts.id", ondelete="CASCADE"), nullable=False)
    method_type: Mapped[ContactMethodType] = mapped_column(_enum_type(ContactMethodType, "contactmethodtype"), nullable=False)
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(_enum_type(VerificationStatus, "verificationstatus"), nullable=False, default=VerificationStatus.UNVERIFIED)
    verification_source: Mapped[str | None] = mapped_column(String(255))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)


class CompanyICPAssessment(Base):
    __tablename__ = "company_icp_assessments"
    __table_args__ = (UniqueConstraint("organization_id", "company_id", name="uq_company_icp_assessments"), CheckConstraint("score >= 0 AND score <= 100", name="ck_company_icp_score"), Index("ix_company_icp_assessments_org_company", "organization_id", "company_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[IcpClassification] = mapped_column(_enum_type(IcpClassification, "icpclassification"), nullable=False)
    factors: Mapped[list[dict[str, Any]]] = mapped_column(_json_type(), nullable=False)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CompanyOpportunityAssessment(Base):
    __tablename__ = "company_opportunity_assessments"
    __table_args__ = (UniqueConstraint("organization_id", "company_id", name="uq_company_opportunity_assessments"), CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="ck_company_opportunity_score"), CheckConstraint("warehouse_fit_score >= 0 AND warehouse_fit_score <= 100", name="ck_company_opportunity_warehouse_fit"), CheckConstraint("demand_score >= 0 AND demand_score <= 100", name="ck_company_opportunity_demand"), CheckConstraint("geographic_score >= 0 AND geographic_score <= 100", name="ck_company_opportunity_geography"), CheckConstraint("contact_score >= 0 AND contact_score <= 100", name="ck_company_opportunity_contact"), Index("ix_company_opportunity_assessments_org_company", "organization_id", "company_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[OpportunityPriority] = mapped_column(_enum_type(OpportunityPriority, "opportunitypriority"), nullable=False)
    warehouse_fit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    demand_score: Mapped[int] = mapped_column(Integer, nullable=False)
    geographic_score: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_score: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class CompanyNextBestAction(Base):
    __tablename__ = "company_next_best_actions"
    __table_args__ = (UniqueConstraint("organization_id", "company_id", name="uq_company_next_best_action"), Index("ix_company_next_best_actions_org_company", "organization_id", "company_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[NextBestActionType] = mapped_column(_enum_type(NextBestActionType, "nextbestactiontype"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())