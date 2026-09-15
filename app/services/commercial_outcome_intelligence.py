from collections import defaultdict
from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.deal import Deal
from app.models.lead import Lead
from app.schemas.commercial_outcome_intelligence import OutcomeCount, OutcomeSummary


class CommercialOutcomeIntelligenceService:
    """Read-only historical aggregates from closed Deal records.

    This service intentionally reports observed counts, not forecasts or inferred
    causation. Missing provenance is retained as an explicit unknown bucket.
    """

    @staticmethod
    def _rate(won: int, closed: int) -> float | None:
        return round(won * 100 / closed, 2) if closed else None

    def _group(self, deals, key_fn) -> list[OutcomeCount]:
        groups = defaultdict(lambda: [0, 0])
        for deal in deals:
            key = key_fn(deal) or "UNKNOWN"
            groups[key][0] += 1
            if deal.deal_status == "WON":
                groups[key][1] += 1
        return [
            OutcomeCount(category=key, closed_deals=values[0], won_deals=values[1],
                         lost_deals=values[0] - values[1], win_rate=self._rate(values[1], values[0]))
            for key, values in sorted(groups.items())
        ]

    def summary(self, db: Session, organization_id: int, *, from_date: date | None = None,
                to_date: date | None = None) -> OutcomeSummary:
        stmt = (
            select(Deal)
            .options(joinedload(Deal.lead).joinedload(Lead.company), joinedload(Deal.selected_warehouse_match))
            .where(Deal.organization_id == organization_id, Deal.deal_status != "OPEN")
            .order_by(Deal.closed_at, Deal.id)
        )
        if from_date:
            stmt = stmt.where(Deal.closed_at >= datetime.combine(from_date, time.min, tzinfo=timezone.utc))
        if to_date:
            stmt = stmt.where(Deal.closed_at < datetime.combine(to_date, time.max, tzinfo=timezone.utc))
        deals = list(db.scalars(stmt).unique())
        won = sum(deal.deal_status == "WON" for deal in deals)
        lost = sum(deal.deal_status == "LOST" for deal in deals)
        lost_deals = [deal for deal in deals if deal.deal_status == "LOST"]
        return OutcomeSummary(
            organization_id=organization_id,
            as_of=datetime.now(timezone.utc),
            from_date=from_date,
            to_date=to_date,
            closed_deals=len(deals), won_deals=won, lost_deals=lost,
            win_rate=self._rate(won, len(deals)),
            categorized_lost_deals=sum(deal.lost_reason_category is not None for deal in lost_deals),
            uncategorized_lost_deals=sum(deal.lost_reason_category is None for deal in lost_deals),
            lost_reasons=self._group(lost_deals, lambda deal: getattr(deal.lost_reason_category, "value", None)),
            industries=self._group(deals, lambda deal: deal.lead.company.industry if deal.lead and deal.lead.company else None),
            lead_sources=self._group(deals, lambda deal: getattr(deal.lead.lead_source, "value", None) if deal.lead else None),
            warehouse_matches=self._group(deals, lambda deal: str(deal.selected_warehouse_match_id) if deal.selected_warehouse_match_id else None),
            limitations=[
                "Aggregates describe historical association and do not establish causation or predictive probability.",
                "Deals closed before structured outcome fields were introduced may remain uncategorized.",
                "Warehouse pilot classifications and market-signal provenance are not directly linked to Deal records.",
            ],
        )