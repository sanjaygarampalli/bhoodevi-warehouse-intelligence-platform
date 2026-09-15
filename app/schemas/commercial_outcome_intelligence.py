from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OutcomeCount(BaseModel):
    category: str
    closed_deals: int
    won_deals: int
    lost_deals: int
    win_rate: float | None


class OutcomeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: int
    as_of: datetime
    from_date: date | None
    to_date: date | None
    closed_deals: int
    won_deals: int
    lost_deals: int
    win_rate: float | None
    categorized_lost_deals: int
    uncategorized_lost_deals: int
    lost_reasons: list[OutcomeCount]
    industries: list[OutcomeCount]
    lead_sources: list[OutcomeCount]
    warehouse_matches: list[OutcomeCount]
    limitations: list[str]