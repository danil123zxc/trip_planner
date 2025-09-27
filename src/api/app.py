"""FastAPI surface for the trip planner agentic workflow."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, AsyncGenerator, Dict, List, Literal, Mapping, Optional, Tuple
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_xai import ChatXAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from src.core.config import ApiSettings
from src.core.domain import (
    ActivitiesAgentOutput,
    BudgetEstimate,
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
from src.pipelines.rag import RetrievalConfig, RetrievalPipeline, create_default_pipeline
from src.services.amadeus import create_amadeus_client, create_flight_search_tool
from src.services.trip_advisor import create_trip_advisor_client, create_trip_advisor_tools
from src.tools.internet_search import create_internet_tool
from src.tools.reddit_search import create_reddit_tool
from src.workflows.planner import build_research_agents, build_research_graph


REQUIRED_SETTINGS = [
    "openai_api_key",
    "tavily_api_key",
    "reddit_client_id",
    "reddit_client_secret",
    "trip_advisor_api_key",
    "amadeus_api_key",
    "amadeus_api_secret",
]

DEFAULT_RECURSION_LIMIT = int(os.getenv("GRAPH_RECURSION_LIMIT", "100"))


class PlanRequest(BaseModel):
    """Request payload used to start a new planning run."""

    context: Context = Field(..., description="Structured trip configuration containing destination, dates, and travellers")
    thread_id: Optional[str] = Field(
        default=None,
        description="Existing planning thread identifier. If omitted a new thread is created.",
    )
    user_prompt: Optional[str] = Field(
        default=None,
        description="Optional free-form instructions injected as the first human message.",
    )


class ResumeSelections(BaseModel):
    """Indices of options chosen during human-in-the-loop review."""

    lodging: Optional[int] = Field(
        default=None,
        ge=0,
        description="Index of the selected lodging option (0-based).",
    )
    intercity_transport: Optional[int] = Field(
        default=None,
        ge=0,
        description="Index of the selected intercity transport option (0-based).",
    )
    activities: Optional[List[int]] = Field(
        default=None,
        description="Indices of activity options to keep. Empty list means keep all.",
    )
    food: Optional[List[int]] = Field(
        default=None,
        description="Indices of food options to keep. Empty list means keep all.",
    )


class ResumeRequest(BaseModel):
    """Request payload used to resume the graph after an interrupt."""

    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="LangGraph configuration object returned by the interrupt response.",
    )
    selections: ResumeSelections = Field(
        default_factory=ResumeSelections,
        description="Indices indicating which options the user selected.",
    )
    research_plan: Optional[Dict[str, CandidateResearch]] = Field(
        default=None,
        description="Optional overrides for the next research plan. Keys align with CandidateResearch fields.",
    )


class PlanningResponse(BaseModel):
    """Unified response returned by both the start and resume endpoints."""

    thread_id: str = Field(..., description="Unique identifier for the planning session")
    status: Literal["interrupt", "complete", "needs_follow_up", "no_plan"] = Field(
        ..., description="Current workflow status"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="Configuration needed to resume when status is 'interrupt'"
    )
    estimated_budget: Optional[BudgetEstimate] = Field(
        default=None, description="Latest budget estimate produced by the workflow"
    )
    research_plan: Optional[ResearchPlan] = Field(
        default=None, description="Latest research plan produced by the workflow"
    )
    lodging: Optional[LodgingAgentOutput] = Field(
        default=None, description="Candidate lodging options surfaced by the agent"
    )
    activities: Optional[ActivitiesAgentOutput] = Field(
        default=None, description="Candidate activities surfaced by the agent"
    )
    food: Optional[FoodAgentOutput] = Field(
        default=None, description="Candidate food options surfaced by the agent"
    )
    intercity_transport: Optional[IntercityTransportAgentOutput] = Field(
        default=None, description="Candidate intercity transport options surfaced by the agent"
    )
    recommendations: Optional[RecommendationsOutput] = Field(
        default=None, description="General travel recommendations"
    )
    final_plan: Optional[FinalPlan] = Field(
        default=None, description="Completed travel plan when the workflow finishes"
    )
    interrupt: Optional[Dict[str, Any]] = Field(
        default=None, description="Raw interrupt payload containing pending human tasks"
    )
    messages: List[str] = Field(
        default_factory=list, description="Workflow execution log rendered as plain strings"
    )


def _ensure_configuration(settings: ApiSettings) -> None:
    missing = [field for field in REQUIRED_SETTINGS if not getattr(settings, field)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            "Missing required environment variables for planner workflow: " f"{joined}"
        )


class WorkflowBundle:
    """Container that wires tools, agents, graph, and shared state together."""

    def __init__(self, settings: ApiSettings) -> None:
        _ensure_configuration(settings)
        settings.apply_langsmith_tracing()

        self.settings = settings
        self.recursion_limit = DEFAULT_RECURSION_LIMIT

        self.llm = ChatXAI(
            model="GROK_4_FAST_REASONING",
            temperature=0,
            api_key=settings.ensure("xai_api_key"),
        )

        self.retrieval_pipeline = self._build_retrieval_pipeline()
        self.trip_client = create_trip_advisor_client(settings)
        self.trip_tools = create_trip_advisor_tools(self.trip_client)
        self.flight_client = create_amadeus_client(settings)
        self.flight_tool = create_flight_search_tool(self.flight_client)

        self.reddit_tool = create_reddit_tool(settings, self.retrieval_pipeline)
        self.internet_tool = create_internet_tool(settings, self.retrieval_pipeline)
        self.search_db_tool = self.retrieval_pipeline.as_tool(
            name="search_db",
            description="Search the internal travel research vector store.",
        )

        self.agents = build_research_agents(
            self.llm,
            comprehensive_search_tool=self.trip_tools["comprehensive_search_tool"],
            flight_search_tool=self.flight_tool,
            search_tools=[self.search_db_tool, self.reddit_tool, self.internet_tool],
        )

        review_mode = os.getenv("HUMAN_REVIEW_MODE", "auto")
        self.graph = build_research_graph(
            llm=self.llm,
            agents=self.agents,
            human_review=review_mode,
            memory=InMemorySaver(),
        )

        self._contexts: Dict[str, Context] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._pending_states: Dict[str, Mapping[str, Any]] = {}
        self._pending_interrupts: Dict[str, Dict[str, Any]] = {}

    def _build_retrieval_pipeline(self) -> RetrievalPipeline:
        config = RetrievalConfig(openai_api_key=self.settings.ensure("openai_api_key"))
        return create_default_pipeline(config)

    def _make_config(self, thread_id: str) -> Dict[str, Any]:
        return {
            "recursion_limit": self.recursion_limit,
            "configurable": {"thread_id": thread_id},
        }

    def _store_result(self, thread_id: str, result: Mapping[str, Any]) -> None:
        self._pending_states[thread_id] = result
        raw_interrupt = result.get("__interrupt__")
        if raw_interrupt:
            first = raw_interrupt[0]
            payload = getattr(first, "value", first)
            if isinstance(payload, Mapping):
                self._pending_interrupts[thread_id] = dict(payload)
        else:
            self._pending_interrupts.pop(thread_id, None)

    def _build_resume_payload(
        self,
        *,
        thread_id: str,
        selections: ResumeSelections,
        research_plan: Optional[Dict[str, CandidateResearch]],
    ) -> Dict[str, Any]:
        state = self._pending_states.get(thread_id)
        if state is None:
            raise RuntimeError(f"No pending state for thread '{thread_id}' to resume.")

        payload: Dict[str, Any] = {}
        if research_plan:
            payload["research_plan"] = {
                key: value.model_dump(exclude_none=True)
                for key, value in research_plan.items()
            }

        def resolve_options(key: str, attr: str) -> List[Any]:  # type: ignore[return-type]
            output = state.get(key)
            if output is None:
                return []
            options = getattr(output, attr, None)
            return list(options or [])

        single_map = {
            "lodging": ("lodging", selections.lodging),
            "intercity_transport": ("transport", selections.intercity_transport),
        }
        for key, (attr, index) in single_map.items():
            if index is None:
                continue
            options = resolve_options(key, attr)
            if not options:
                raise RuntimeError(f"No options stored for '{key}' to select from.")
            if index < 0 or index >= len(options):
                raise RuntimeError(f"Selection index {index} is out of range for '{key}'.")
            payload[key] = options[index].model_dump(exclude_none=True)

        multi_map = {
            "activities": ("activities", selections.activities),
            "food": ("food", selections.food),
        }
        for key, (attr, indices) in multi_map.items():
            if indices is None:
                continue
            options = resolve_options(key, attr)
            if not options:
                raise RuntimeError(f"No options stored for '{key}' to select from.")
            if indices:
                selected = []
                for idx in indices:
                    if idx < 0 or idx >= len(options):
                        raise RuntimeError(
                            f"Selection index {idx} is out of range for '{key}'."
                        )
                    selected.append(options[idx])
            else:
                selected = options
            dumps = [item.model_dump(exclude_none=True) for item in selected]
            payload[key] = dumps[0] if len(dumps) == 1 else dumps

        return payload

    async def close(self) -> None:
        await self.trip_client.aclose()

    async def plan_trip(
        self,
        *,
        context: Context,
    ) -> Tuple[str, Dict[str, Any], Mapping[str, Any]]:
        active_thread = f"trip_{uuid4()}"
        config = self._configs.get(active_thread) or self._make_config(active_thread)

        self._contexts[active_thread] = context
        self._configs[active_thread] = config

        messages = []
        initial_state = State(messages=messages)

        result = await self.graph.ainvoke(
            initial_state,
            context=context,
            config=config,
        )
        self._store_result(active_thread, result)
        return active_thread, config, result

    async def resume_trip(
        self,
        *,
        thread_id: str,
        config: Optional[Dict[str, Any]],
        selections: ResumeSelections,
        research_plan: Optional[Dict[str, CandidateResearch]],
    ) -> Tuple[Dict[str, Any], Mapping[str, Any]]:
        if thread_id not in self._contexts:
            raise RuntimeError(f"Unknown planning thread '{thread_id}'.")

        active_config = config or self._configs.get(thread_id) or self._make_config(thread_id)
        self._configs[thread_id] = active_config

        resume_payload = self._build_resume_payload(
            thread_id=thread_id,
            selections=selections,
            research_plan=research_plan,
        )

        command = Command(resume=resume_payload)
        context = self._contexts[thread_id]
        result = await self.graph.ainvoke(command, context=context, config=active_config)
        self._store_result(thread_id, result)
        return active_config, result


def _messages_to_strings(result: Mapping[str, Any]) -> List[str]:
    raw_messages = result.get("messages", [])
    rendered: List[str] = []
    for message in raw_messages:
        if isinstance(message, BaseMessage):
            content = getattr(message, "content", None)
            if isinstance(content, str):
                rendered.append(content)
            else:
                rendered.append(repr(message))
        else:
            rendered.append(str(message))
    return rendered


def _extract_interrupt(result: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    raw = result.get("__interrupt__")
    if not raw:
        return None
    first = raw[0]
    payload = getattr(first, "value", first)
    if isinstance(payload, Mapping):
        return dict(payload)
    return None


def _determine_status(result: Mapping[str, Any]) -> Literal["interrupt", "complete", "needs_follow_up", "no_plan"]:
    if "__interrupt__" in result:
        return "interrupt"
    final_plan = result.get("final_plan")
    if final_plan and getattr(final_plan, "research_plan", None):
        return "needs_follow_up"
    if final_plan:
        return "complete"
    return "no_plan"


def _result_to_response(
    thread_id: str,
    config: Dict[str, Any],
    result: Mapping[str, Any],
) -> PlanningResponse:
    status = _determine_status(result)
    interrupt_payload = _extract_interrupt(result)

    return PlanningResponse(
        thread_id=thread_id,
        status=status,
        config=config,
        estimated_budget=result.get("estimated_budget"),
        research_plan=result.get("research_plan"),
        lodging=result.get("lodging"),
        activities=result.get("activities"),
        food=result.get("food"),
        intercity_transport=result.get("intercity_transport"),
        recommendations=result.get("recommendations"),
        final_plan=result.get("final_plan"),
        interrupt=interrupt_payload,
        messages=_messages_to_strings(result),
    )


@lru_cache(maxsize=1)
def get_workflow_bundle() -> WorkflowBundle:
    settings = ApiSettings.from_env()
    return WorkflowBundle(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        yield
    finally:
        bundle = get_workflow_bundle()
        await bundle.close()


app = FastAPI(title="Trip Planner API", version="0.1.0", lifespan=lifespan)


@app.post("/plan/start", response_model=PlanningResponse)
async def start_planning(payload: PlanRequest) -> PlanningResponse:
    """Start the planning workflow and return the first state (interrupt or final)."""

    bundle = get_workflow_bundle()
    try:
        thread_id, config, result = await bundle.plan_trip(
            context=payload.context
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safeguards unexpected graph failures
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _result_to_response(thread_id, config, result)


@app.post("/plan/resume/{thread_id}", response_model=PlanningResponse)
async def resume_planning(thread_id: str, payload: ResumeRequest) -> PlanningResponse:
    """Resume the planning workflow after collecting human feedback."""

    bundle = get_workflow_bundle()
    try:
        config, result = await bundle.resume_trip(
            thread_id=thread_id,
            config=payload.config,
            selections=payload.selections,
            research_plan=payload.research_plan,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safeguards unexpected graph failures
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _result_to_response(thread_id, config, result)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health endpoint used for readiness probes."""

    return {"status": "healthy", "service": "trip-planner-api"}
