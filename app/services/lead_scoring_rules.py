"""Central v1 policy. Changes to weights or eligibility require a new version."""
from dataclasses import dataclass

from app.models.lead import LeadPriority
from app.models.lead_activity import ActivityType


SCORING_VERSION = "v1"
PRIORITY_THRESHOLDS = (
    (75, LeadPriority.URGENT),
    (50, LeadPriority.HIGH),
    (25, LeadPriority.MEDIUM),
    (0, LeadPriority.LOW),
)
VIABLE_MATCH_SCORE = 50
HIGH_MATCH_SCORE = 80
MEANINGFUL_ACTIVITY_TYPES = frozenset({
    ActivityType.CALL, ActivityType.EMAIL, ActivityType.LINKEDIN,
    ActivityType.WHATSAPP, ActivityType.MEETING, ActivityType.PROPOSAL,
})


@dataclass(frozen=True)
class ScoringRule:
    points: int
    awarded: str
    missing: str


SCORING_RULES = {
    "company.associated": ScoringRule(5, "Company is associated with the lead.", "No associated company."),
    "company.organization": ScoringRule(3, "Company has an owning organization.", "Company ownership is missing."),
    "company.industry": ScoringRule(2, "Company industry is recorded; relevance is not inferred.", "Company industry is missing."),
    "company.legal_name": ScoringRule(2, "Company legal name is recorded.", "Company legal name is missing."),
    "company.website": ScoringRule(3, "Company website is recorded, not independently verified.", "Company website is missing."),
    "company.location": ScoringRule(3, "Company headquarters city and state are recorded.", "Company headquarters city or state is missing."),
    "company.products": ScoringRule(2, "Company products are described.", "Company products are not described."),
    "decision_maker.exists": ScoringRule(5, "A named, non-disqualified company contact exists.", "No named, non-disqualified company contact exists."),
    "decision_maker.designation": ScoringRule(3, "Selected contact has a designation and a recognized decision level.", "Selected contact lacks a designation or recognized decision level."),
    "decision_maker.email": ScoringRule(5, "Selected contact has an email recorded, not independently verified.", "Selected contact has no email recorded."),
    "decision_maker.phone": ScoringRule(5, "Selected contact has a phone recorded, not independently verified.", "Selected contact has no phone recorded."),
    "decision_maker.multiple": ScoringRule(2, "At least two company contacts have contact details.", "Fewer than two company contacts have contact details."),
    "requirement.active": ScoringRule(5, "An active requirement exists.", "No active requirement exists."),
    "requirement.size": ScoringRule(8, "Selected active requirement has positive area and consistent bounds.", "Selected active requirement lacks valid positive area or has inconsistent bounds."),
    "requirement.location": ScoringRule(6, "Selected active requirement specifies a city or pincode.", "Selected active requirement lacks a city or pincode."),
    "requirement.urgency": ScoringRule(5, "Selected active requirement needs move-in immediately or within three months.", "Selected active requirement has no immediate or one-to-three-month move-in need."),
    "requirement.budget": ScoringRule(4, "Selected active requirement has a positive budget per sqft.", "Selected active requirement lacks a positive budget per sqft."),
    "requirement.details": ScoringRule(2, "Selected active requirement specifies warehouse type and goods or storage type.", "Selected active requirement lacks warehouse type and goods/storage details."),
    "activity.completed": ScoringRule(3, "A completed lead activity is recorded.", "No completed lead activity is recorded."),
    "activity.meaningful": ScoringRule(5, "Completed outreach, meeting or proposal activity is recorded.", "No completed outreach, meeting or proposal activity is recorded."),
    "activity.positive": ScoringRule(4, "Latest completed meaningful activity records INTERESTED or CALLBACK_SCHEDULED.", "Latest completed meaningful activity has no positive recorded outcome."),
    "activity.follow_up": ScoringRule(3, "A non-cancelled activity records a follow-up after its activity date.", "No non-cancelled activity records a follow-up after its activity date."),
    "warehouse_match.viable": ScoringRule(5, "An available warehouse has an eligible match scoring at least 50.", "No available warehouse has an eligible match scoring at least 50."),
    "warehouse_match.high_quality": ScoringRule(7, "An eligible available-warehouse match scores at least 80.", "No eligible available-warehouse match scores at least 80."),
    "warehouse_match.multiple": ScoringRule(3, "At least two distinct available warehouses have viable matches.", "Fewer than two distinct available warehouses have viable matches."),
}


def classify_priority(score: int) -> LeadPriority:
    if not 0 <= score <= 100:
        raise ValueError("Lead score must be between 0 and 100")
    return next(priority for threshold, priority in PRIORITY_THRESHOLDS if score >= threshold)