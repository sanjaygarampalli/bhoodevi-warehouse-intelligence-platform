"""End-to-end integration test for the full lead-to-deal business workflow.

Tests the orchestration endpoints introduced by the workflow service,
exercising the complete pipeline:

1. Create industry → organization → company → lead
2. Create decision maker for the lead's company
3. Create an active requirement
4. Create a warehouse
5. Generate warehouse matches
6. Qualify the lead (``POST /workflow/leads/{id}/qualify``)
7. Seed default pipeline (``POST /workflow/organizations/{id}/pipeline/seed``)
8. Create an opportunity (``POST /workflow/leads/{id}/opportunities``)
9. Verify the deal exists with the correct context

Prerequisites: all existing domain CRUD tests pass at baseline.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User


# ── helpers ────────────────────────────────────────────────────────────

def _token(email: str) -> str:
    return "Bearer " + create_access_token({"sub": email})


def post(client, path, payload=None, expected=200):
    """POST json and assert status."""
    response = client.post(path, json=payload or {})
    assert response.status_code == expected, (
        f"POST {path} → {response.status_code}: {response.text}"
    )
    return response.json() if response.text else response


def put(client, path, payload, expected=200):
    response = client.put(path, json=payload)
    assert response.status_code == expected, (
        f"PUT {path} → {response.status_code}: {response.text}"
    )
    return response.json() if response.text else response


def get(client, path, expected=200):
    response = client.get(path)
    assert response.status_code == expected, (
        f"GET {path} → {response.status_code}: {response.text}"
    )
    return response.json() if response.text else response
# ── fixture ────────────────────────────────────────────────────────────

@pytest.fixture()
def ctx():
    """Provide an isolated in-memory DB with a TestClient and two users."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()

    db.add_all([
        User(
            id=1,
            full_name="Admin Alpha",
            email="e2e-admin@example.com",
            role="admin",
            hashed_password="unused",
        ),
        User(
            id=2,
            full_name="Regular User",
            email="e2e-user@example.com",
            role="user",
            hashed_password="unused",
        ),
    ])
    db.commit()

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db

    try:
        with TestClient(app) as client:
            client.headers["Authorization"] = _token("e2e-admin@example.com")
            yield client, db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


# ── tests ──────────────────────────────────────────────────────────────

class TestEndToEndWorkflow:
    """Full business journey from industry seeding through deal creation."""

    def test_qualify_lead_validates_prerequisites(self, ctx):
        """A brand-new lead without a decision maker or active requirement
        cannot be qualified.
        """
        client, db = ctx

        # 1. industry
        ind = post(client, "/industries/", {"code": "E2E", "name": "E2E Test Industry"})
        # 2. organisation
        org = post(client, "/organizations/", {
            "org_code": "E2E", "legal_name": "E2E Corp",
            "org_type": "PVT_LTD", "subscription_tier": "FREE",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        # 3. company
        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "E2E Prospect",
            "industry": ind["name"], "company_type": "Private",
        })
        # 4. lead
        lead = post(client, "/leads/", {
            "lead_number": "E2E-001", "company_id": company["id"],
        })

        # Qualification should fail — no decision maker, no requirement.
        resp = client.post(f"/workflow/leads/{lead['id']}/qualify")
        assert resp.status_code == 400, resp.text
        assert "decision maker" in resp.text.lower()
    def test_full_workflow_happy_path(self, ctx):
            """Complete E2E: create prerequisites → qualify → seed pipeline
            → create opportunity → verify.
            """
            client, db = ctx

            # ── Step 1: infrastructure ────────────────────────────────────
            ind = post(client, "/industries/", {"code": "E2A", "name": "Warehousing"})
            org = post(client, "/organizations/", {
                "org_code": "E2A", "legal_name": "Alpha E2E",
                "org_type": "PVT_LTD", "subscription_tier": "GROWTH",
                "status": "ACTIVE", "industry_id": ind["id"],
            })
            company = post(client, "/companies/", {
                "organization_id": org["id"], "company_name": "Alpha Prospect",
                "industry": ind["name"], "company_type": "Private",
            })
            lead = post(client, "/leads/", {
                "lead_number": "E2A-001", "company_id": company["id"],
            })

            # ── Step 2: decision maker for the company ────────────────────
            dm = post(client, "/decision-makers/", {
                "company_id": company["id"], "full_name": "Jane Doe",
                "designation": "Logistics Head",
                "decision_level": "DIRECTOR",
                "email": "jane@alphaprospect.example",
            })

            # ── Step 3: active requirement ─────────────────────────────────
            req = post(client, f"/leads/{lead['id']}/requirements/", {
                "lead_id": lead["id"], "title": "Cold storage 5000",
                "minimum_area": 5000,
                "preferred_city": "Bengaluru",
                "requirement_status": "ACTIVE",
            })

            # ── Step 4: warehouse + matches ───────────────────────────────
            wh = post(client, "/warehouses/", {
                "warehouse_name": "E2E Cold Storage",
                "owner_id": 1, "city": "Bengaluru", "state": "Karnataka",
                "total_area_sqft": 10000, "warehouse_type": "COVERED",
                "availability_status": "AVAILABLE",
            })
            # Generate matches
            post(client, f"/warehouse-matches/requirements/{req['id']}/generate", {})

            matches = get(client, f"/warehouse-matches/?requirement_id={req['id']}")
            assert len(matches) >= 1, "No warehouse matches generated"

            # ── Step 5: qualify the lead ──────────────────────────────────
            qual = post(client, f"/workflow/leads/{lead['id']}/qualify")
            assert qual["status"] == "QUALIFIED"
            assert qual["previous_status"] == "NEW"
            assert qual["company_id"] == company["id"]
            assert qual["id"] == lead["id"]

            # Idempotent re-qualify is a no-op.
            qual2 = post(client, f"/workflow/leads/{lead['id']}/qualify")
            assert qual2["status"] == "QUALIFIED"
            assert qual2["previous_status"] == "QUALIFIED"

            # ── Step 6: seed default pipeline stages ──────────────────────
            seed = post(client, f"/workflow/organizations/{org['id']}/pipeline/seed")
            assert seed["stages_created"] == 5
            assert seed["stages_present"] == 5
            assert seed["organization_id"] == org["id"]

            # Idempotent re-seed does not create duplicates.
            seed2 = post(client, f"/workflow/organizations/{org['id']}/pipeline/seed")
            assert seed2["stages_created"] == 0
            assert seed2["stages_present"] == 5

            # ── Step 7: create opportunity (deal) from the lead ───────────
            stages = get(client, f"/deal-pipeline-stages/?organization_id={org['id']}")
            stages_by_key = {s["stage_key"]: s for s in stages}
            stage_id = stages_by_key["QUALIFICATION"]["id"]

            opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
                "deal_name": "Bengaluru Cold Storage Deal",
                "stage_id": stage_id,
                "expected_revenue": "1250000.00",
                "currency": "INR",
                "notes": "Created via E2E workflow",
            })
            assert opp["deal_id"] > 0
            assert opp["deal_name"] == "Bengaluru Cold Storage Deal"
            assert opp["lead_id"] == lead["id"]
            assert opp["requirement_id"] == req["id"]
            assert opp["selected_warehouse_match_id"] is not None
            assert opp["organization_id"] == org["id"]
            assert opp["stage_id"] == stage_id
            assert opp["deal_status"] == "OPEN"
            assert opp["lead_status"] == "POSITIONED"
            assert opp["initial_task_id"] is not None
            assert opp["created_at"] is not None

            # ── Step 8: verify the deal is readable via the deal endpoint ─
            deal = get(client, f"/deals/{opp['deal_id']}")
            assert deal["id"] == opp["deal_id"]
            assert deal["deal_name"] == opp["deal_name"]
            assert deal["deal_status"] == "OPEN"
            assert deal["stage"]["id"] == stage_id
            assert deal["organization_id"] == org["id"]

            # ── Step 9: verify the opportunity context is accessible ──────
            opportunity = get(client, f"/deals/{opp['deal_id']}/opportunity")
            assert opportunity["deal"]["id"] == opp["deal_id"]
            assert opportunity["lead"]["id"] == lead["id"]
            assert opportunity["requirement"]["id"] == req["id"]
            assert opportunity["organization"]["id"] == org["id"]
    def test_qualify_rejects_disqualified_lead(self, ctx):
            """A lead with status DISQUALIFIED cannot be qualified."""
            client, db = ctx

            ind = post(client, "/industries/", {"code": "E2B", "name": "E2B Test"})
            org = post(client, "/organizations/", {
                "org_code": "E2B", "legal_name": "E2B Inc",
                "org_type": "PVT_LTD", "subscription_tier": "FREE",
                "status": "ACTIVE", "industry_id": ind["id"],
            })
            company = post(client, "/companies/", {
                "organization_id": org["id"], "company_name": "E2B Co",
                "industry": ind["name"], "company_type": "Private",
            })
            lead = post(client, "/leads/", {
                "lead_number": "E2B-001", "company_id": company["id"],
            })

            # Manually disqualify the lead.
            put(client, f"/leads/{lead['id']}", {"status": "DISQUALIFIED"})

            resp = client.post(f"/workflow/leads/{lead['id']}/qualify")
            assert resp.status_code == 400, resp.text
            assert "cannot qualify" in resp.text.lower()

    def test_create_opportunity_requires_qualified_lead(self, ctx):
        """A lead that is not QUALIFIED cannot be used to create an opportunity."""
        client, db = ctx

        ind = post(client, "/industries/", {"code": "E2C", "name": "E2C Test"})
        org = post(client, "/organizations/", {
            "org_code": "E2C", "legal_name": "E2C LLC",
            "org_type": "PVT_LTD", "subscription_tier": "FREE",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        # Pre-create a pipeline stage for this organisation.
        post(client, "/deal-pipeline-stages/", {
            "organization_id": org["id"], "stage_key": "QUALIFICATION",
            "stage_name": "Qualification", "stage_order": 10,
        })

        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "E2C Co",
            "industry": ind["name"], "company_type": "Private",
        })
        lead = post(client, "/leads/", {
            "lead_number": "E2C-001", "company_id": company["id"],
        })

        stages = get(client, f"/deal-pipeline-stages/?organization_id={org['id']}")
        stage_id = stages[0]["id"]

        resp = client.post(f"/workflow/leads/{lead['id']}/opportunities", json={
            "deal_name": "Invalid Deal",
            "stage_id": stage_id,
        })
        assert resp.status_code == 400, resp.text
        assert "qualified" in resp.text.lower()

    def test_unauthenticated_workflow_access_is_rejected(self, ctx):
        """Workflow endpoints require authentication."""
        client, db = ctx
        client.headers.pop("Authorization", None)

        for path in ("/workflow/leads/1/qualify",
                     "/workflow/organizations/1/pipeline/seed"):
            resp = client.post(path)
            assert resp.status_code in (401, 403), f"{path} → {resp.status_code}"

    def test_missing_lead_returns_404(self, ctx):
        """Qualifying a non-existent lead returns 404."""
        client, db = ctx
        resp = client.post("/workflow/leads/99999/qualify")
        assert resp.status_code == 404, resp.text

    def test_missing_organization_returns_404(self, ctx):
        """Seeding pipeline for a non-existent org returns 404."""
        client, db = ctx
        resp = client.post("/workflow/organizations/99999/pipeline/seed")
        assert resp.status_code == 404, resp.text

    def test_disqualify_lead_workflow(self, ctx):
        """Disqualify a lead via the workflow endpoint records reason."""
        client, db = ctx
        ind = post(client, "/industries/", {"code": "E2D", "name": "E2D Dq Test"})
        org = post(client, "/organizations/", {
            "org_code": "E2D", "legal_name": "E2D Inc",
            "org_type": "PVT_LTD", "subscription_tier": "FREE",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "E2D Co",
            "industry": ind["name"], "company_type": "Private",
        })
        lead = post(client, "/leads/", {
            "lead_number": "E2D-001", "company_id": company["id"],
        })
        result = post(client, f"/workflow/leads/{lead['id']}/disqualify", {
            "reason": "Budget too low",
        })
        assert result["status"] == "DISQUALIFIED"
        assert result["previous_status"] == "NEW"
        updated = get(client, f"/leads/{lead['id']}")
        assert updated["disqualified_reason"] == "Budget too low"

    def test_disqualify_rejects_terminal_lead(self, ctx):
        """A lead already DISQUALIFIED cannot be disqualified again."""
        client, db = ctx
        ind = post(client, "/industries/", {"code": "E2E", "name": "E2E Term Test"})
        org = post(client, "/organizations/", {
            "org_code": "E2E", "legal_name": "E2E Term Inc",
            "org_type": "PVT_LTD", "subscription_tier": "FREE",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "E2E Term Co",
            "industry": ind["name"], "company_type": "Private",
        })
        lead = post(client, "/leads/", {
            "lead_number": "E2E-002", "company_id": company["id"],
        })
        post(client, f"/workflow/leads/{lead['id']}/disqualify", {
            "reason": "No warehouses",
        })
        resp = client.post(f"/workflow/leads/{lead['id']}/disqualify", json={"reason": "Again"})
        assert resp.status_code == 400, resp.text

    def test_opportunity_advances_lead_to_positioned(self, ctx):
        """After opportunity creation the lead advances to POSITIONED."""
        client, db = ctx
        ind = post(client, "/industries/", {"code": "E2F", "name": "E2F Pos Test"})
        org = post(client, "/organizations/", {
            "org_code": "E2F", "legal_name": "E2F Pos Inc",
            "org_type": "PVT_LTD", "subscription_tier": "GROWTH",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "E2F Pos Co",
            "industry": ind["name"], "company_type": "Private",
        })
        lead = post(client, "/leads/", {
            "lead_number": "E2F-001", "company_id": company["id"],
        })
        post(client, "/decision-makers/", {
            "company_id": company["id"], "full_name": "Mark",
            "designation": "CEO", "decision_level": "DIRECTOR",
            "email": "mark@e2f.example",
        })
        req = post(client, f"/leads/{lead['id']}/requirements/", {
            "lead_id": lead["id"], "title": "Space 3000",
            "minimum_area": 3000, "preferred_city": "Mumbai",
            "requirement_status": "ACTIVE",
        })
        post(client, "/warehouses/", {
            "warehouse_name": "E2F Wh",
            "owner_id": 1, "city": "Mumbai", "state": "Maharashtra",
            "total_area_sqft": 8000, "warehouse_type": "COVERED",
            "availability_status": "AVAILABLE",
        })
        post(client, f"/warehouse-matches/requirements/{req['id']}/generate", {})
        qual = post(client, f"/workflow/leads/{lead['id']}/qualify")
        assert qual["status"] == "QUALIFIED"
        post(client, f"/workflow/organizations/{org['id']}/pipeline/seed")
        stages = get(client, f"/deal-pipeline-stages/?organization_id={org['id']}")
        stage_id = next(s["id"] for s in stages if s["stage_key"] == "QUALIFICATION")
        opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
            "deal_name": "E2F Pos Deal", "stage_id": stage_id,
            "expected_revenue": "500000.00",
        })
        assert opp["lead_status"] == "POSITIONED"
        updated_lead = get(client, f"/leads/{lead['id']}")
        assert updated_lead["status"] == "POSITIONED"

    def test_opportunity_creates_initial_follow_up_task(self, ctx):
        """Opportunity creation generates a follow-up task automatically."""
        client, db = ctx
        ind = post(client, "/industries/", {"code": "E2G", "name": "E2G Task Test"})
        org = post(client, "/organizations/", {
            "org_code": "E2G", "legal_name": "E2G Task Inc",
            "org_type": "PVT_LTD", "subscription_tier": "GROWTH",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "E2G Task Co",
            "industry": ind["name"], "company_type": "Private",
        })
        lead = post(client, "/leads/", {
            "lead_number": "E2G-001", "company_id": company["id"],
        })
        post(client, "/decision-makers/", {
            "company_id": company["id"], "full_name": "Sarah",
            "designation": "VP Ops", "decision_level": "DIRECTOR",
            "email": "sarah@e2g.example",
        })
        req = post(client, f"/leads/{lead['id']}/requirements/", {
            "lead_id": lead["id"], "title": "Storage 2000",
            "minimum_area": 2000, "preferred_city": "Delhi",
            "requirement_status": "ACTIVE",
        })
        post(client, "/warehouses/", {
            "warehouse_name": "E2G Wh", "owner_id": 1,
            "city": "Delhi", "state": "Delhi",
            "total_area_sqft": 5000, "warehouse_type": "COVERED",
            "availability_status": "AVAILABLE",
        })
        post(client, f"/warehouse-matches/requirements/{req['id']}/generate", {})
        post(client, f"/workflow/leads/{lead['id']}/qualify")
        post(client, f"/workflow/organizations/{org['id']}/pipeline/seed")
        stages = get(client, f"/deal-pipeline-stages/?organization_id={org['id']}")
        stage_id = next(s["id"] for s in stages if s["stage_key"] == "QUALIFICATION")
        opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
            "deal_name": "E2G Task Deal", "stage_id": stage_id,
            "expected_revenue": "750000.00",
        })
        tasks = get(client, f"/follow-up-tasks/?deal_id={opp['deal_id']}")
        assert len(tasks) >= 1, "No follow-up task created"
        task = tasks[0]
        assert task["lead_id"] == lead["id"]
        assert task["deal_id"] == opp["deal_id"]
        assert "present proposal" in task["subject"].lower()

    def test_opportunity_with_requirement_id_override(self, ctx):
        """Creating an opportunity with explicit requirement_id."""
        client, db = ctx
        ind = post(client, "/industries/", {"code": "E2H", "name": "E2H Override"})
        org = post(client, "/organizations/", {
            "org_code": "E2H", "legal_name": "E2H Override Inc",
            "org_type": "PVT_LTD", "subscription_tier": "GROWTH",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "E2H Override Co",
            "industry": ind["name"], "company_type": "Private",
        })
        lead = post(client, "/leads/", {
            "lead_number": "E2H-001", "company_id": company["id"],
        })
        post(client, "/decision-makers/", {
            "company_id": company["id"], "full_name": "Tester",
            "designation": "Manager", "decision_level": "MANAGER",
            "email": "tester@e2h.example",
        })
        req1 = post(client, f"/leads/{lead['id']}/requirements/", {
            "lead_id": lead["id"], "title": "Req A",
            "minimum_area": 1000, "preferred_city": "Pune",
            "requirement_status": "ACTIVE",
        })
        req2 = post(client, f"/leads/{lead['id']}/requirements/", {
            "lead_id": lead["id"], "title": "Req B",
            "minimum_area": 2000, "preferred_city": "Pune",
            "requirement_status": "ACTIVE",
        })
        post(client, "/warehouses/", {
            "warehouse_name": "E2H Wh", "owner_id": 1,
            "city": "Pune", "state": "Maharashtra",
            "total_area_sqft": 10000, "warehouse_type": "COVERED",
            "availability_status": "AVAILABLE",
        })
        post(client, f"/warehouse-matches/requirements/{req1['id']}/generate", {})
        post(client, f"/warehouse-matches/requirements/{req2['id']}/generate", {})
        post(client, f"/workflow/leads/{lead['id']}/qualify")
        post(client, f"/workflow/organizations/{org['id']}/pipeline/seed")
        stages = get(client, f"/deal-pipeline-stages/?organization_id={org['id']}")
        stage_id = next(s["id"] for s in stages if s["stage_key"] == "QUALIFICATION")
        opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
            "deal_name": "E2H Override Deal", "stage_id": stage_id,
            "requirement_id": req2["id"], "expected_revenue": "300000.00",
        })
        assert opp["requirement_id"] == req2["id"]
        deal = get(client, f"/deals/{opp['deal_id']}")
        assert deal["requirement_id"] == req2["id"]

    def test_disqualify_endpoint_requires_auth(self, ctx):
        """Disqualify returns 401/403 without auth."""
        client, db = ctx
        client.headers.pop("Authorization", None)
        resp = client.post("/workflow/leads/1/disqualify", json={"reason": "N/A"})
        assert resp.status_code in (401, 403)
class TestLeadLifecycle:
    """End-to-end tests for the lead lifecycle state machine.

    Tests use the helper functions from the parent module.  Each test sets
    up the minimal context (industry → organization → company → lead)
    before exercising the transition endpoint.
    """

    def _setup_minimal(self, client, db):
        """Create the minimum entities needed to work with a lead."""
        ind = post(client, "/industries/", {"code": "LLC", "name": "LLC Test"})
        org = post(client, "/organizations/", {
            "org_code": "LLC", "legal_name": "LLC Test Inc",
            "org_type": "PVT_LTD", "subscription_tier": "GROWTH",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "LLC Test Co",
            "industry": ind["name"], "company_type": "Private",
        })
        lead = post(client, "/leads/", {
            "lead_number": "LLC-001", "company_id": company["id"],
        })
        decision_maker = post(client, "/decision-makers/", {
            "company_id": company["id"], "full_name": "LLC Manager",
            "designation": "Manager", "decision_level": "MANAGER",
            "email": "llc@example.com",
        })
        return ind, org, company, lead, decision_maker

    def test_transition_new_to_discovered(self, ctx):
        """NEW to DISCOVERED is a valid lifecycle transition."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        result = post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "DISCOVERED",
            "reason": "Found via LinkedIn research",
        })
        assert result["status"] == "DISCOVERED"
        assert result["previous_status"] == "NEW"
        assert result["transition_reason"] == "Found via LinkedIn research"

    def test_transition_new_to_contacted(self, ctx):
        """NEW to CONTACTED is valid (skips DISCOVERED)."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        result = post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "CONTACTED",
        })
        assert result["status"] == "CONTACTED"
        assert result["previous_status"] == "NEW"
    def test_transition_contacted_to_qualified(self, ctx):
        """CONTACTED to QUALIFIED transition is valid."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "CONTACTED",
        })
        result = post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "QUALIFIED",
            "reason": "Lead expressed interest",
        })
        assert result["status"] == "QUALIFIED"
        assert result["previous_status"] == "CONTACTED"

    def test_transition_new_to_negotiating_rejected(self, ctx):
        """NEW to NEGOTIATING is rejected by the state machine."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        resp = client.post(f"/workflow/leads/{lead['id']}/transition", json={
            "new_status": "NEGOTIATING",
        })
        assert resp.status_code == 400, (
            f"Expected 400, got {resp.status_code}: {resp.text}"
        )

    def test_transition_discovered_to_dormant(self, ctx):
        """DISCOVERED to DORMANT is valid."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "DISCOVERED",
        })
        result = post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "DORMANT",
            "reason": "No response after multiple attempts",
        })
        assert result["status"] == "DORMANT"
        assert result["previous_status"] == "DISCOVERED"
    def test_transition_to_terminal_rejected(self, ctx):
        """Transition endpoint rejects terminal statuses (WON, LOST, DISQUALIFIED)."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        for terminal in ("WON", "LOST", "DISQUALIFIED"):
            resp = client.post(f"/workflow/leads/{lead['id']}/transition", json={
                "new_status": terminal,
            })
            assert resp.status_code == 400, (
                f"Expected 400 for {terminal}, got {resp.status_code}: {resp.text}"
            )

    def test_transition_unknown_status(self, ctx):
        """Unknown target status returns 400."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        resp = client.post(f"/workflow/leads/{lead['id']}/transition", json={
            "new_status": "ALIEN_STATUS",
        })
        assert resp.status_code == 400, (
            f"Expected 400, got {resp.status_code}: {resp.text}"
        )

    def test_transition_same_status_is_noop(self, ctx):
        """Transitioning to the current status is a no-op."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        result = post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "NEW",
        })
        assert result["status"] == "NEW"
        assert result["previous_status"] == "NEW"
    def test_transition_case_insensitive(self, ctx):
        """The new_status field is case-insensitive."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        result = post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "  discovered  ",  # Extra spaces and lowercase
        })
        assert result["status"] == "DISCOVERED"

    def test_transition_nonexistent_lead(self, ctx):
        """Transition on a nonexistent lead returns 404."""
        client, db = ctx
        resp = client.post("/workflow/leads/999999/transition", json={
            "new_status": "DISCOVERED",
        })
        assert resp.status_code == 404

    def test_transition_disqualified_lead_rejected(self, ctx):
        """Cannot transition a DISQUALIFIED lead."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        post(client, f"/workflow/leads/{lead['id']}/disqualify", {
            "reason": "Not a fit",
        })
        resp = client.post(f"/workflow/leads/{lead['id']}/transition", json={
            "new_status": "DISCOVERED",
        })
        assert resp.status_code == 400, (
            f"Expected 400, got {resp.status_code}: {resp.text}"
        )

    def test_transition_requires_admin(self, ctx):
        """Transition requires admin auth."""
        from app.core.security import create_access_token
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        client.headers["Authorization"] = "Bearer " + create_access_token(
            {"sub": "e2e-user@example.com"}
        )
        resp = client.post(f"/workflow/leads/{lead['id']}/transition", json={
            "new_status": "DISCOVERED",
        })
        assert resp.status_code in (401, 403)

    def test_transition_unauthorized_no_token(self, ctx):
        """Transition without auth returns 401/403."""
        client, db = ctx
        client.headers.pop("Authorization", None)
        resp = client.post("/workflow/leads/1/transition", json={
            "new_status": "DISCOVERED",
        })
        assert resp.status_code in (401, 403)

    def test_qualify_response_includes_disqualified_reason(self, ctx):
        """disqualified_reason field is present in disqualify response."""
        client, db = ctx
        _, _, _, lead, _ = self._setup_minimal(client, db)
        result = post(client, f"/workflow/leads/{lead['id']}/disqualify", {
            "reason": "Budget too low",
        })
        assert result["disqualified_reason"] == "Budget too low"
        assert result["status"] == "DISQUALIFIED"
        assert result["previous_status"] == "NEW"
class TestDealLeadLifecycleIntegration:
    """Tests for automated lead status advancement on deal closure.

    Uses the workflow-level ``/workflow/deals/{deal_id}/transition``
    endpoint which wraps the standard deal transition and advances the
    lead to WON/LOST when the deal reaches a terminal stage.
    """

    def _full_setup(self, client, db):
        """Build a complete pipeline-ready context."""
        ind = post(client, "/industries/", {"code": "DLL", "name": "DLL Test"})
        org = post(client, "/organizations/", {
            "org_code": "DLL", "legal_name": "DLL Test Inc",
            "org_type": "PVT_LTD", "subscription_tier": "GROWTH",
            "status": "ACTIVE", "industry_id": ind["id"],
        })
        company = post(client, "/companies/", {
            "organization_id": org["id"], "company_name": "DLL Test Co",
            "industry": ind["name"], "company_type": "Private",
        })
        lead = post(client, "/leads/", {
            "lead_number": "DLL-001", "company_id": company["id"],
        })
        post(client, "/decision-makers/", {
            "company_id": company["id"], "full_name": "DLL Manager",
            "designation": "Manager", "decision_level": "MANAGER",
            "email": "dll@example.com",
        })
        req = post(client, f"/leads/{lead['id']}/requirements/", {
            "lead_id": lead["id"], "title": "DLL Req",
            "minimum_area": 5000, "preferred_city": "Pune",
            "requirement_status": "ACTIVE",
        })
        post(client, "/warehouses/", {
            "warehouse_name": "DLL Wh", "owner_id": 1,
            "city": "Pune", "state": "Maharashtra",
            "total_area_sqft": 20000, "warehouse_type": "COVERED",
            "availability_status": "AVAILABLE",
        })
        post(client, f"/warehouse-matches/requirements/{req['id']}/generate", {})
        post(client, f"/workflow/leads/{lead['id']}/qualify")
        post(client, f"/workflow/organizations/{org['id']}/pipeline/seed")
        stages = get(client, f"/deal-pipeline-stages/?organization_id={org['id']}")
        return ind, org, company, lead, req, stages
    def test_deal_won_advances_lead_to_won(self, ctx):
        """Closing a deal as WON advances lead from POSITIONED to WON."""
        client, db = ctx
        *_, lead, _, stages = self._full_setup(client, db)
        qual_stage = next(s for s in stages if s["stage_key"] == "QUALIFICATION")
        opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
            "deal_name": "DLL Won Deal", "stage_id": qual_stage["id"],
            "expected_revenue": "1000000.00",
        })
        assert opp["lead_status"] == "POSITIONED"
        lead = get(client, f"/leads/{lead['id']}")
        assert lead["status"] == "POSITIONED"
        neg_stage = next(s for s in stages if s["stage_key"] == "NEGOTIATION")
        post(client, f"/workflow/deals/{opp['deal_id']}/transition", {
            "to_stage_id": neg_stage["id"],
            "change_reason": "Moving to negotiation",
        })
        won_stage = next(s for s in stages if s["stage_key"] == "CLOSED_WON")
        deal = post(client, f"/workflow/deals/{opp['deal_id']}/transition", {
            "to_stage_id": won_stage["id"],
            "change_reason": "Customer signed",
        })
        assert deal["deal_status"] == "WON"
        lead = get(client, f"/leads/{lead['id']}")
        assert lead["status"] == "WON"

    def test_deal_won_from_negotiating(self, ctx):
        """WON works from NEGOTIATING lead status as well."""
        client, db = ctx
        *_, lead, _, stages = self._full_setup(client, db)
        qual_stage = next(s for s in stages if s["stage_key"] == "QUALIFICATION")
        opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
            "deal_name": "DLL Neg Deal", "stage_id": qual_stage["id"],
            "expected_revenue": "500000.00",
        })
        post(client, f"/workflow/leads/{lead['id']}/transition", {
            "new_status": "NEGOTIATING",
        })
        lead = get(client, f"/leads/{lead['id']}")
        assert lead["status"] == "NEGOTIATING"
        won_stage = next(s for s in stages if s["stage_key"] == "CLOSED_WON")
        post(client, f"/workflow/deals/{opp['deal_id']}/transition", {
            "to_stage_id": won_stage["id"],
            "change_reason": "Negotiation successful",
        })
        lead = get(client, f"/leads/{lead['id']}")
        assert lead["status"] == "WON"
    def test_deal_lost_advances_lead_to_lost(self, ctx):
        """Closing a deal as LOST advances lead from POSITIONED to LOST."""
        client, db = ctx
        *_, lead, _, stages = self._full_setup(client, db)
        qual_stage = next(s for s in stages if s["stage_key"] == "QUALIFICATION")
        opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
            "deal_name": "DLL Lost Deal", "stage_id": qual_stage["id"],
            "expected_revenue": "250000.00",
        })
        lost_stage = next(s for s in stages if s["stage_key"] == "CLOSED_LOST")
        post(client, f"/workflow/deals/{opp['deal_id']}/transition", {
            "to_stage_id": lost_stage["id"],
            "change_reason": "Customer chose competitor",
        })
        lead = get(client, f"/leads/{lead['id']}")
        assert lead["status"] == "LOST"
        assert lead["closed_reason"] == "Customer chose competitor"

    def test_deal_non_terminal_keeps_lead_positioned(self, ctx):
        """Non-terminal deal transitions do not affect lead status."""
        client, db = ctx
        *_, lead, _, stages = self._full_setup(client, db)
        qual_stage = next(s for s in stages if s["stage_key"] == "QUALIFICATION")
        opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
            "deal_name": "DLL Safe Deal", "stage_id": qual_stage["id"],
            "expected_revenue": "100000.00",
        })
        lead = get(client, f"/leads/{lead['id']}")
        assert lead["status"] == "POSITIONED"
        pos_stage = next(s for s in stages if s["stage_key"] == "POSITIONING")
        post(client, f"/workflow/deals/{opp['deal_id']}/transition", {
            "to_stage_id": pos_stage["id"],
            "change_reason": "Internal review",
        })
        lead = get(client, f"/leads/{lead['id']}")
        assert lead["status"] == "POSITIONED"
    def test_standard_deal_transition_does_not_advance_lead(self, ctx):
        """Using the standard /deals/{id}/transition (not workflow) does not
        automatically advance lead status."""
        client, db = ctx
        *_, lead, _, stages = self._full_setup(client, db)
        qual_stage = next(s for s in stages if s["stage_key"] == "QUALIFICATION")
        opp = post(client, f"/workflow/leads/{lead['id']}/opportunities", {
            "deal_name": "DLL Std Deal", "stage_id": qual_stage["id"],
        })
        won_stage = next(s for s in stages if s["stage_key"] == "CLOSED_WON")
        post(client, f"/deals/{opp['deal_id']}/transition", {
            "to_stage_id": won_stage["id"],
            "change_reason": "Direct close",
        })
        # Lead remains POSITIONED (only workflow transition advances lead)
        lead = get(client, f"/leads/{lead['id']}")
        assert lead["status"] == "POSITIONED"