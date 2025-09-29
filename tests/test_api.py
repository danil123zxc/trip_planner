"""Tests for the FastAPI application."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api import app as api_app
from src.core.domain import (
    BudgetEstimate,
    CandidateLodging,
    FinalPlan,
    LodgingAgentOutput,
)


class StubBundle:
    """Test double that mimics the workflow bundle used by the API."""

    def __init__(self) -> None:
        self.plan_trip_call = None
        self.resume_trip_call = None
        self.plan_trip_result = (
            "stub-thread",
            {"recursion_limit": 100, "configurable": {"thread_id": "stub-thread"}},
            {},
        )
        self.resume_trip_result = (
            {"recursion_limit": 100, "configurable": {"thread_id": "stub-thread"}},
            {},
        )

    async def plan_trip(self, *, context, user_prompt):  # type: ignore[override]
        self.plan_trip_call = {
            "context": context,
            "user_prompt": user_prompt,
        }
        return self.plan_trip_result

    async def resume_trip(
        self,
        *,
        config,
        selections,
        research_plan,
    ):  # type: ignore[override]
        thread_id = None
        if config:
            thread_id = config.get("configurable", {}).get("thread_id")
        self.resume_trip_call = {
            "thread_id": thread_id,
            "config": config,
            "selections": selections,
            "research_plan": research_plan,
        }
        return self.resume_trip_result

    async def close(self):  # pragma: no cover - no-op for tests
        return None


@pytest.fixture
def stub_bundle(monkeypatch) -> StubBundle:
    """Provide a stubbed workflow bundle for API tests."""

    bundle = StubBundle()
    api_app.get_workflow_bundle.cache_clear()
    monkeypatch.setattr(api_app, "get_workflow_bundle", lambda: bundle)
    return bundle


@pytest.fixture
def client(stub_bundle: StubBundle) -> TestClient:
    """Yield a TestClient that uses the stubbed workflow bundle."""

    with TestClient(api_app.app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient):
    """Health endpoint should report a healthy service."""

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "trip-planner-api"}


def test_plan_start_returns_interrupt_payload(client: TestClient, stub_bundle: StubBundle):
    """Starting the planner should surface interrupt metadata when available."""

    budget = BudgetEstimate(
        currency="USD",
        intercity_transport=400,
        local_transport=200,
        food=600,
        activities=500,
        lodging=700,
        other=100,
        budget_per_day=350,
    )
    lodging = LodgingAgentOutput(lodging=[CandidateLodging(name="Hotel Aurora")])
    interrupt_payload = {
        "task": "Choose lodging option",
        "selections": [
            {
                "type": "lodging",
                "task": "Choose lodging option",
                "options": [lodging.lodging[0].model_dump(exclude_none=True)],
            }
        ],
    }

    stub_bundle.plan_trip_result = (
        "stub-thread",
        {"recursion_limit": 100, "configurable": {"thread_id": "stub-thread"}},
        {
            "__interrupt__": [SimpleNamespace(value=interrupt_payload)],
            "messages": [],
            "estimated_budget": budget,
            "lodging": lodging,
        },
    )

    request_payload = {
        "context": {
            "destination": "Tokyo",
            "destination_country": "Japan",
            "date_from": "2025-01-10",
            "date_to": "2025-01-17",
            "budget": 2500,
            "currency": "USD",
            "group_type": "couple",
        }
    }

    response = client.post("/plan/start", json=request_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "interrupt"
    assert data["thread_id"] == "stub-thread"
    assert data["config"]["configurable"]["thread_id"] == "stub-thread"
    assert data["interrupt"] == interrupt_payload
    assert data["lodging"]["lodging"][0]["name"] == "Hotel Aurora"

def test_plan_start_forwards_user_prompt(client: TestClient, stub_bundle: StubBundle):
    """User prompt should be passed through to the workflow bundle."""

    request_payload = {
        "context": {
            "destination": "Osaka",
            "destination_country": "Japan",
            "date_from": "2025-02-01",
            "date_to": "2025-02-05",
            "budget": 1800,
            "currency": "USD",
            "group_type": "friends",
        },
        "user_prompt": "Focus on street food options",
    }

    response = client.post("/plan/start", json=request_payload)
    assert response.status_code == 200
    assert stub_bundle.plan_trip_call["user_prompt"] == "Focus on street food options"
    assert stub_bundle.plan_trip_call["context"].destination == "Osaka"


def test_plan_resume_without_thread_id_errors(client: TestClient, stub_bundle: StubBundle):
    """Resume should fail clearly when the workflow config lacks a thread id."""

    stub_bundle.resume_trip_result = ({}, {})

    request_payload = {
        "config": {},
        "selections": {},
    }

    response = client.post("/plan/resume", json=request_payload)
    assert response.status_code == 500
    assert "thread_id" in response.json()["detail"]
def test_plan_resume_returns_final_plan(client: TestClient, stub_bundle: StubBundle):
    """Resuming the planner should surface the final plan when available."""

    final_plan = FinalPlan(total_budget=2500, currency="USD")
    stub_bundle.resume_trip_result = (
        {"recursion_limit": 100, "configurable": {"thread_id": "stub-thread"}},
        {"messages": [], "final_plan": final_plan},
    )

    request_payload = {
        "config": {"recursion_limit": 100, "configurable": {"thread_id": "stub-thread"}},
        "selections": {"lodging": 0},
    }

    response = client.post("/plan/resume", json=request_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["final_plan"]["total_budget"] == 2500
    assert data["thread_id"] == "stub-thread"
