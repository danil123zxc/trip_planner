"""Unit tests for the trip planner workflow (nodes + compiled graph)."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple, Type

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import CompiledGraph
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.core.domain import (
    ActivitiesAgentOutput,
    CandidateActivity,
    CandidateFood,
    CandidateIntercityTransport,
    CandidateLodging,
    CandidateResearch,
    Context,
    FinalPlan,
    FoodAgentOutput,
    IntercityTransportAgentOutput,
    LodgingAgentOutput,
    RecommendationsOutput,
    ResearchPlan,
    State,
)
from src.workflows import planner


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class StructuredResponder:
    """Mimics the object returned by `llm.with_structured_output`."""

    def __init__(self, parent: "StubLLM", model_cls: Type[Any], response: Any):
        self._parent = parent
        self._model_cls = model_cls
        self._response = response

    async def ainvoke(self, prompt: str) -> Any:
        self._parent.calls.append((self._model_cls, prompt))
        return self._response


class StubLLM:
    """Captures prompts and yields preconfigured structured responses."""

    def __init__(self) -> None:
        self.responses: Dict[Type[Any], Any] = {}
        self.calls: List[Tuple[Type[Any], str]] = []

    def set_response(self, model_cls: Type[Any], value: Any) -> None:
        self.responses[model_cls] = value

    def with_structured_output(self, model_cls: Type[Any]) -> StructuredResponder:
        try:
            value = self.responses[model_cls]
        except KeyError as exc:  # pragma: no cover - protects against missing test fixtures
            raise AssertionError(f"No stubbed response for {model_cls}") from exc
        return StructuredResponder(self, model_cls, value)


class DummyAgent:
    """Minimal async agent that records prompts and returns canned payloads."""

    def __init__(self, response: Any) -> None:
        self.response = response
        self.seen_prompts: List[str] = []

    async def ainvoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        messages = payload.get("messages", [])
        if messages and isinstance(messages[0], (HumanMessage, AIMessage)):
            self.seen_prompts.append(messages[0].content)  # type: ignore[arg-type]
        return {
            "structured_response": self.response,
            "messages": [AIMessage(content="ack")],
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_context() -> Context:
    return Context(
        travellers=[],
        budget=2500,
        currency="USD",
        destination="Tokyo",
        destination_country="Japan",
        date_from=date(2025, 1, 10),
        date_to=date(2025, 1, 17),
        group_type="couple",
    )


@pytest.fixture
def stub_components(monkeypatch) -> Tuple[StubLLM, planner.ResearchAgents]:
    monkeypatch.setattr(
        planner, "get_coordinates_nominatim", lambda *_, **__: "35.6895,139.6917"
    )

    llm = StubLLM()
    llm.set_response(
        planner.BudgetEstimate,
        planner.BudgetEstimate(
            budget_level="$$",
            currency="USD",
            intercity_transport=400,
            local_transport=200,
            food=600,
            activities=500,
            lodging=700,
            other=100,
            budget_per_day=350,
        ),
    )
    llm.set_response(
        ResearchPlan,
        ResearchPlan(
            lodging_candidates=CandidateResearch(candidates_number=2),
            activities_candidates=CandidateResearch(candidates_number=2),
            food_candidates=CandidateResearch(candidates_number=2),
            intercity_transport_candidates=CandidateResearch(candidates_number=1),
            recommendations=CandidateResearch(candidates_number=1),
        ),
    )

    lodging_options = [
        CandidateLodging(name="Hotel Aurora"),
        CandidateLodging(name="Hotel Horizon"),
    ]
    activity_options = [
        CandidateActivity(name="Sushi Workshop"),
        CandidateActivity(name="Night Tour"),
    ]
    food_options = [
        CandidateFood(name="Ramen House"),
        CandidateFood(name="Izakaya Corner"),
    ]
    transport_options = [
        CandidateIntercityTransport(name="Bullet Train"),
        CandidateIntercityTransport(name="Express Flight"),
    ]

    final_plan = FinalPlan(
        total_budget=2500,
        currency="USD",
        lodging=lodging_options[0],
        intercity_transport=transport_options[0],
    )
    llm.set_response(FinalPlan, final_plan)

    agents = planner.ResearchAgents(
        lodging=DummyAgent(LodgingAgentOutput(lodging=lodging_options)),
        activities=DummyAgent(ActivitiesAgentOutput(activities=activity_options)),
        food=DummyAgent(FoodAgentOutput(food=food_options)),
        intercity_transport=DummyAgent(
            IntercityTransportAgentOutput(transport=transport_options)
        ),
        recommendations=DummyAgent(
            RecommendationsOutput(safety_level="moderate", child_friendly_rating=3)
        ),
    )

    planner.configure_workflow_nodes(planner.WorkflowComponents(llm=llm, agents=agents))
    return llm, agents


@pytest.fixture
def base_state() -> State:
    return State(messages=[])


# ---------------------------------------------------------------------------
# Node-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_estimate_node_returns_estimate(base_state, sample_context, stub_components):
    llm, _ = stub_components
    runtime = Runtime(context=sample_context)

    result = await planner.budget_estimate_node(base_state, runtime)

    assert "estimated_budget" in result
    assert result["messages"][0].name == "budget_estimate"
    assert llm.calls and llm.calls[0][0] is planner.BudgetEstimate


@pytest.mark.asyncio
async def test_research_plan_node_sets_coordinates(base_state, sample_context, stub_components):
    llm, _ = stub_components
    runtime = Runtime(context=sample_context)

    outcome = await planner.research_plan_node(base_state, runtime)

    assert outcome["destination_coordinates"] == "35.6895,139.6917"
    assert outcome["research_plan"].activities_candidates.candidates_number == 2
    assert llm.calls[-1][0] is ResearchPlan


@pytest.mark.asyncio
async def test_lodging_node_calls_agent(base_state, sample_context, stub_components):
    _, agents = stub_components
    runtime = Runtime(context=sample_context)

    result = await planner.lodging_node(base_state, runtime)

    assert "lodging" in result
    assert agents.lodging.seen_prompts


@pytest.mark.asyncio
async def test_activities_node_calls_agent(base_state, sample_context, stub_components):
    _, agents = stub_components
    runtime = Runtime(context=sample_context)

    result = await planner.activities_node(base_state, runtime)

    assert "activities" in result
    assert agents.activities.seen_prompts


@pytest.mark.asyncio
async def test_food_node_calls_agent(base_state, sample_context, stub_components):
    _, agents = stub_components
    runtime = Runtime(context=sample_context)

    result = await planner.food_node(base_state, runtime)

    assert "food" in result
    assert agents.food.seen_prompts


@pytest.mark.asyncio
async def test_intercity_transport_node_calls_agent(base_state, sample_context, stub_components):
    _, agents = stub_components
    runtime = Runtime(context=sample_context)

    result = await planner.intercity_transport_node(base_state, runtime)

    assert "intercity_transport" in result
    assert agents.intercity_transport.seen_prompts


@pytest.mark.asyncio
async def test_recommendations_node_calls_agent(base_state, sample_context, stub_components):
    _, agents = stub_components
    runtime = Runtime(context=sample_context)

    result = await planner.recommendations_node(base_state, runtime)

    assert "recommendations" in result
    assert agents.recommendations.seen_prompts


@pytest.mark.asyncio
async def test_planner_node_returns_final_plan(base_state, sample_context, stub_components):
    llm, _ = stub_components
    runtime = Runtime(context=sample_context)

    outcome = await planner.planner_node(base_state, runtime)

    assert outcome["final_plan"] == llm.responses[FinalPlan]
    assert outcome["messages"][0].name in {"final_plan", "research_plan"}


@pytest.mark.asyncio
async def test_planner_node_signals_follow_up(sample_context):
    llm = StubLLM()
    llm.set_response(
        planner.BudgetEstimate,
        planner.BudgetEstimate(
            budget_level="$$",
            currency="USD",
            intercity_transport=1,
            local_transport=1,
            food=1,
            activities=1,
            lodging=1,
            other=0,
            budget_per_day=1,
        ),
    )
    llm.set_response(ResearchPlan, ResearchPlan())
    llm.set_response(
        FinalPlan,
        FinalPlan(
            research_plan=ResearchPlan(
                activities_candidates=CandidateResearch(candidates_number=1)
            )
        ),
    )
    agents = planner.ResearchAgents(
        lodging=DummyAgent(LodgingAgentOutput(lodging=[])),
        activities=DummyAgent(ActivitiesAgentOutput(activities=[])),
        food=DummyAgent(FoodAgentOutput(food=[])),
        intercity_transport=DummyAgent(IntercityTransportAgentOutput(transport=[])),
        recommendations=DummyAgent(
            RecommendationsOutput(safety_level="moderate", child_friendly_rating=3)
        ),
    )
    planner.configure_workflow_nodes(planner.WorkflowComponents(llm=llm, agents=agents))

    state = State(messages=[])
    runtime = Runtime(context=sample_context)

    result = await planner.planner_node(state, runtime)

    assert result["final_plan"].research_plan is not None
    assert result["messages"][0].name == "research_plan"


@pytest.mark.asyncio
async def test_auto_selection_node_chooses_first_option(sample_context):
    state = State(
        messages=[],
        lodging=LodgingAgentOutput(
            lodging=[
                CandidateLodging(name="Option A"),
                CandidateLodging(name="Option B"),
            ]
        ),
        intercity_transport=IntercityTransportAgentOutput(
            transport=[
                CandidateIntercityTransport(name="Train"),
                CandidateIntercityTransport(name="Flight"),
            ]
        ),
    )
    runtime = Runtime(context=sample_context)

    result = await planner.auto_selection_node(state, runtime)

    assert result["lodging"].lodging[0].name == "Option A"
    assert result["intercity_transport"].transport[0].name == "Train"


@pytest.mark.asyncio
async def test_combined_human_review_node_no_options(sample_context):
    state = State(messages=[])
    runtime = Runtime(context=sample_context)

    result = await planner.combined_human_review_node(state, runtime)

    assert result == {}


# ---------------------------------------------------------------------------
# Routing and graph wiring
# ---------------------------------------------------------------------------


def test_route_from_planner_handles_follow_up():
    state = State(
        messages=[],
        final_plan=FinalPlan(
            research_plan=ResearchPlan(
                activities_candidates=CandidateResearch(candidates_number=1),
                food_candidates=CandidateResearch(candidates_number=1),
            )
        ),
    )
    runtime = Runtime(context=None)

    edges = planner.route_from_planner(state, runtime)
    assert set(edges) == {"research_activities", "research_food"}


def test_route_from_planner_returns_end():
    assert planner.route_from_planner(State(messages=[]), Runtime(context=None)) == planner.END


def test_build_research_graph_creates_compiled_graph(stub_components):
    llm, agents = stub_components
    graph = planner.build_research_graph(llm=llm, agents=agents, human_review="interrupt")
    assert isinstance(graph, CompiledGraph)


# ---------------------------------------------------------------------------
# Compiled graph integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compiled_graph_auto_mode(sample_context, stub_components):
    llm, agents = stub_components
    graph = planner.build_research_graph(llm=llm, agents=agents, human_review="auto")

    result_state = await graph.ainvoke(
        State(messages=[]),
        context=sample_context,
        config={"configurable": {"thread_id": "auto-mode"}},
    )

    assert result_state.final_plan == llm.responses[FinalPlan]
    assert result_state.lodging.lodging[0].name == "Hotel Aurora"
    assert result_state.intercity_transport.transport[0].name == "Bullet Train"
    assert result_state.destination_coordinates == "35.6895,139.6917"
    assert any(getattr(msg, "name", "") == "final_plan" for msg in result_state.messages)


@pytest.mark.asyncio
async def test_compiled_graph_interrupt_resume(sample_context, stub_components):
    llm, agents = stub_components
    graph = planner.build_research_graph(llm=llm, agents=agents, human_review="interrupt")

    first_pass = await graph.ainvoke(
        State(messages=[]),
        context=sample_context,
        config={"configurable": {"thread_id": "interrupt-mode"}},
    )

    assert "__interrupt__" in first_pass
    selections = {}
    for selection in first_pass["__interrupt__"][0].value["selections"]:
        selections[selection["type"]] = selection["options"][0]

    resumed = await graph.ainvoke(
        Command(resume=selections),
        context=sample_context,
        config={"configurable": {"thread_id": "interrupt-mode"}},
    )

    assert resumed.final_plan == llm.responses[FinalPlan]
    assert resumed.lodging.lodging[0].name == "Hotel Aurora"
    assert resumed.intercity_transport.transport[0].name == "Bullet Train"
