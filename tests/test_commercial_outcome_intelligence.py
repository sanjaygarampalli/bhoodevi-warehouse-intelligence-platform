from app.models.deal import LostReasonCategory
from app.services.commercial_outcome_intelligence import CommercialOutcomeIntelligenceService
from app.services.deal import DealService
from app.schemas.deal import DealTransition
from tests.test_deal import context, create, flow, payload, post


def test_empty_outcome_summary_is_safe(context):
    _, db = context
    result = CommercialOutcomeIntelligenceService().summary(db, organization_id=999)
    assert result.closed_deals == 0
    assert result.won_deals == 0
    assert result.lost_deals == 0
    assert result.win_rate is None
    assert result.lost_reasons == []


def test_terminal_transition_preserves_explicit_outcome_evidence(flow):
    client, db = flow["client"], flow["db"]
    deal = create(flow)
    response = client.post(
        f"/deals/{deal['id']}/transition",
        json={
            "to_stage_id": flow["stages"]["LOST"]["id"],
            "change_reason": "Customer selected a lower-priced option",
            "lost_reason_category": "PRICE",
            "outcome_notes": "Budget was below the available warehouse rate.",
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["deal_status"] == "LOST"
    assert result["lost_reason_category"] == "PRICE"
    assert result["outcome_notes"] == "Budget was below the available warehouse rate."

    summary = CommercialOutcomeIntelligenceService().summary(db, flow["org"]["id"])
    assert (summary.closed_deals, summary.lost_deals, summary.categorized_lost_deals) == (1, 1, 1)
    assert summary.lost_reasons[0].category == LostReasonCategory.PRICE.value


def test_win_rate_uses_only_closed_deals(flow):
    client, db = flow["client"], flow["db"]
    deal = create(flow)
    assert client.post(f"/deals/{deal['id']}/transition", json={"to_stage_id": flow["stages"]["WON"]["id"]}).status_code == 200
    summary = CommercialOutcomeIntelligenceService().summary(db, flow["org"]["id"])
    assert summary.closed_deals == 1
    assert summary.won_deals == 1
    assert summary.win_rate == 100.0


def test_terminal_outcome_evidence_cannot_be_changed_on_retry(flow):
    deal = create(flow)
    db = flow["db"]
    DealService().transition_deal(
        db, deal["id"], DealTransition(to_stage_id=flow["stages"]["LOST"]["id"], lost_reason_category=LostReasonCategory.TIMING),
    )
    try:
        DealService().transition_deal(
            db, deal["id"], DealTransition(to_stage_id=flow["stages"]["LOST"]["id"], lost_reason_category=LostReasonCategory.PRICE),
        )
    except Exception as exc:
        assert "cannot be changed" in str(exc)
    else:
        raise AssertionError("Conflicting terminal outcome evidence was accepted")