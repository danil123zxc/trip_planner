"""Integration-focused tests for the Trip Planner FastAPI surface."""
from __future__ import annotations

from datetime import date


from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from src.api import app as api_app
from src.core.domain import (
    ActivitiesAgentOutput,
    BudgetEstimate,
    CandidateActivity,
    CandidateFood,
    CandidateIntercityTransport,
    CandidateLodging,
    CandidateResearch,
    FinalPlan,
    FoodAgentOutput,
    IntercityTransportAgentOutput,
    LodgingAgentOutput,
    PlanForDay,
    ResearchPlan,
    Transfer,
)


def _make_context_payload() -> Dict[str, Any]:
    """Return a representative planning context payload."""

    return {
        "destination": "Tokyo",
        "destination_country": "Japan",
        "date_from": "2025-01-10",
        "date_to": "2025-01-17",
        "budget": 2500,
        "currency": "USD",
        "group_type": "couple",
        "travellers": [
            {"name": "Jordan", "date_of_birth": "1992-04-12"},
            {"name": "Riley", "date_of_birth": "1991-08-03"},
        ],
        "trip_purpose": "vacation",
    }


def _make_budget_estimate() -> BudgetEstimate:
    return BudgetEstimate(
        budget_level="$$",
        currency="USD",
        intercity_transport=400,
        local_transport=150,
        food=500,
        activities=450,
        lodging=800,
        other=100,
        budget_per_day=350,
        notes="Sample budget for testing",
    )


def _make_research_plan() -> ResearchPlan:
    return ResearchPlan(
        lodging_candidates=CandidateResearch(name="lodging", candidates_number=2),
        activities_candidates=CandidateResearch(name="activities", candidates_number=3),
        food_candidates=CandidateResearch(name="food", candidates_number=2),
        intercity_transport_candidates=CandidateResearch(name="intercity", candidates_number=1),
    )


def _make_lodging_candidate() -> CandidateLodging:
    return CandidateLodging(
        name="Hotel Aurora",
        price_level="$$",
        rating=4.6,
        area="Shinjuku",
        price_night=180,
    )


def _make_activity_candidate(name: str = "Senso-ji Temple Walk") -> CandidateActivity:
    return CandidateActivity(name=name, tags=["cultural"])


def _make_food_candidate() -> CandidateFood:
    return CandidateFood(name="Ichiran Ramen", tags=["ramen"])


def _make_transport_candidate() -> CandidateIntercityTransport:
    return CandidateIntercityTransport(
        name="Shinkansen to Kyoto",
        transfer=[Transfer(name="Shinkansen", place="Tokyo Station")],
        total_duration_min=160,
    )


def _make_interrupt_payload(lodging: CandidateLodging) -> Dict[str, Any]:
    return {
        "task": "Confirm lodging selection",
        "selections": [
            {
                "type": "lodging",
                "task": "Confirm lodging selection",
                "options": [lodging.model_dump(exclude_none=True)],
            }
        ],
    }


def _make_final_plan() -> FinalPlan:
    activity = _make_activity_candidate("Asakusa Morning Walk")
    food = _make_food_candidate()
    lodging = _make_lodging_candidate()
    transport = _make_transport_candidate()
    return FinalPlan(
        days=[
            PlanForDay(
                day_number=1,
                day_date=date(2025, 1, 10),
                activities=[activity],
                food=[food],
                intracity_moves=[],
                day_budget=320,
            )
        ],
        total_budget=2400,
        currency="USD",
        lodging=lodging,
        intercity_transport=transport,
    )


class StubBundle:
    """Asynchronous stub that mimics the workflow bundle used by the API."""

    def __init__(self) -> None:
        self.thread_id = "stub-thread"
        self.plan_trip_inputs: List[Any] = []
        self.resume_trip_inputs: List[Any] = []
        self.plan_trip_result = self._default_plan_trip_result()
        self.resume_trip_result = self._default_resume_result()

    def _default_plan_trip_result(self) -> Any:
        config = {"recursion_limit": 100, "configurable": {"thread_id": self.thread_id}}
        lodging = _make_lodging_candidate()
        interrupt_payload = _make_interrupt_payload(lodging)
        result = {
            "__interrupt__": [SimpleNamespace(value=interrupt_payload)],
            "messages": [],
            "estimated_budget": _make_budget_estimate(),
            "research_plan": _make_research_plan(),
            "lodging": LodgingAgentOutput(lodging=[lodging]),
            "activities": ActivitiesAgentOutput(activities=[_make_activity_candidate()]),
            "food": FoodAgentOutput(food=[_make_food_candidate()]),
            "intercity_transport": IntercityTransportAgentOutput(
                transport=[_make_transport_candidate()]
            ),
        }
        return config, result

    def _default_resume_result(self) -> Any:
        config = {"recursion_limit": 100, "configurable": {"thread_id": self.thread_id}}
        result = {
            "messages": ["Workflow resumed"],
            "final_plan": _make_final_plan(),
        }
        return config, result

    async def plan_trip(self, *, context) -> Any:
        self.plan_trip_inputs.append(context)
        return self.plan_trip_result

    async def resume_trip(self, *, context, config, selections, research_plan) -> Any:
        thread_id = None
        if config:
            thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise RuntimeError("Resume config must include configurable.thread_id.")
        self.resume_trip_inputs.append(
            {
                "context": context,
                "config": config,
                "selections": selections,
                "research_plan": research_plan,
            }
        )
        return self.resume_trip_result

    async def close(self) -> None:
        return None


@pytest.fixture
def stub_bundle(monkeypatch) -> StubBundle:
    """Provide a stubbed workflow bundle for API integration tests."""

    bundle = StubBundle()
    api_app.get_workflow_bundle.cache_clear()
    monkeypatch.setattr(api_app, "get_workflow_bundle", lambda: bundle)
    return bundle


@pytest.fixture
def client(stub_bundle: StubBundle) -> TestClient:
    """Yield a TestClient that uses the stubbed workflow bundle."""

    with TestClient(api_app.app) as test_client:
        yield test_client



def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "trip-planner-api"}


def test_plan_start_returns_interrupt_payload(client: TestClient, stub_bundle: StubBundle) -> None:
    payload = {"context": _make_context_payload()}
    response = client.post("/plan/start", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "interrupt"
    assert data["config"]["configurable"]["thread_id"] == stub_bundle.thread_id
    assert data["interrupt"]["task"] == "Confirm lodging selection"
    assert data["lodging"][0]["name"] == "Hotel Aurora"
    assert data["estimated_budget"]["currency"] == "USD"
    assert data["research_plan"]["lodging_candidates"]["candidates_number"] == 2

    last_context = stub_bundle.plan_trip_inputs[-1]
    assert last_context.destination == payload["context"]["destination"]


def test_plan_start_can_return_completed_plan(client: TestClient, stub_bundle: StubBundle) -> None:
    final_plan = _make_final_plan()
    stub_bundle.plan_trip_result = (
        {"recursion_limit": 100, "configurable": {"thread_id": stub_bundle.thread_id}},
        {"messages": ["Done"], "final_plan": final_plan},
    )

    response = client.post("/plan/start", json={"context": _make_context_payload()})

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "complete"
    assert data["final_plan"]["total_budget"] == pytest.approx(2400)
    assert data["final_plan"]["currency"] == "USD"
    assert data["final_plan"]["days"][0]["day_number"] == 1


def test_plan_resume_returns_final_plan(client: TestClient, stub_bundle: StubBundle) -> None:
    context_payload = _make_context_payload()
    start_response = client.post("/plan/start", json={"context": context_payload})
    start_data = start_response.json()
    config = start_data["config"]

    stub_bundle.resume_trip_result = (
        config,
        {"messages": ["Resumed"], "final_plan": _make_final_plan()},
    )

    resume_payload = {
        "config": config,
        "selections": {
            "lodging": 0,
            "intercity_transport": 0
        },
    }

    resume_response = client.post("/plan/resume", json=resume_payload)

    assert resume_response.status_code == 200
    data = resume_response.json()

    assert data["status"] == "complete"
    assert data["final_plan"]["days"][0]["day_date"] == "2025-01-10"
    assert data["final_plan"]["lodging"]["name"] == "Hotel Aurora"

    last_resume = stub_bundle.resume_trip_inputs[-1]
    assert last_resume["context"].destination == context_payload["destination"]
    assert last_resume["selections"].activities == [0]


def test_plan_resume_without_thread_id_errors(client: TestClient, stub_bundle: StubBundle) -> None:
    resume_payload = {
        "config": {"recursion_limit": 25},
        "context": _make_context_payload(),
        "selections": {},
    }

    response = client.post("/plan/resume", json=resume_payload)

    assert response.status_code == 400
    assert "thread_id" in response.json()["detail"]
