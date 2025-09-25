"""FastAPI surface for the trip planner agentic workflow."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from src.core.config import ApiSettings
from src.core.domain import (
    ActivitiesAgentOutput,
    BudgetEstimate,
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


class PlanRequest(BaseModel):
    """API payload describing the trip context and optional user prompt."""

    context: Context = Field(..., description="Structured trip configuration")
    user_prompt: Optional[str] = Field(
        default=None,
        description="Optional free-form instructions added as the first message",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread identifier to keep graph state grouped",
    )


class PlanResponse(BaseModel):
    """Response containing the generated plan and supporting metadata."""

    thread_id: str
    status: str
    final_plan: Optional[FinalPlan] = None
    next_research_plan: Optional[ResearchPlan] = None
    messages: List[str] = Field(default_factory=list)


class InterruptResponse(BaseModel):
    """Response when workflow reaches an interrupt point requiring human input."""
    
    thread_id: str
    status: str = "interrupt"
    estimated_budget: Optional[BudgetEstimate] = None
    research_plan: Optional[ResearchPlan] = None
    lodging: Optional[LodgingAgentOutput] = None
    activities: Optional[ActivitiesAgentOutput] = None
    food: Optional[FoodAgentOutput] = None
    intercity_transport: Optional[IntercityTransportAgentOutput] = None
    recommendations: Optional[RecommendationsOutput] = None
    interrupt_data: Optional[Dict[str, Any]] = None
    messages: List[str] = Field(default_factory=list)


class ResumeRequest(BaseModel):
    """Request to resume workflow after human review."""
    
    thread_id: str = Field(description="Thread ID from the interrupt response")
    human_selections: Dict[str, int] = Field(
        description="Human selections mapping task type to option index",
        example={"lodging": 0, "intercity_transport": 1}
    )


def _ensure_configuration(settings: ApiSettings) -> None:
    missing = [field for field in REQUIRED_SETTINGS if not getattr(settings, field)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            "Missing required environment variables for planner workflow: " f"{joined}"
        )

class WorkflowBundle:
    """Container that wires together tools, agents, and the LangGraph workflow."""

    def __init__(self, settings: ApiSettings) -> None:
        _ensure_configuration(settings)
        settings.apply_langsmith_tracing()

        self.settings = settings

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0,
            api_key=settings.ensure("openai_api_key"),
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

    def _build_retrieval_pipeline(self) -> RetrievalPipeline:
        config = RetrievalConfig(openai_api_key=self.settings.ensure("openai_api_key"))
        return create_default_pipeline(config)

    async def close(self) -> None:
        await self.trip_client.aclose()

    async def plan_trip(
        self,
        context: Context,
        user_prompt: Optional[str],
        thread_id: Optional[str],
    ) -> Tuple[str, State]:
        active_thread = thread_id or f"trip_{uuid4()}"
        messages = [HumanMessage(content=user_prompt)] if user_prompt else []
        state = State(messages=messages)

        result_state = await self.graph.ainvoke(
            state,
            context=context,
            config={"configurable": {"thread_id": active_thread}},
        )
        return active_thread, result_state


@lru_cache(maxsize=1)
def get_workflow_bundle() -> WorkflowBundle:
    settings = ApiSettings.from_env()
    return WorkflowBundle(settings)


def _state_messages_to_strings(state: State) -> List[str]:
    rendered: List[str] = []
    for message in state.messages:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            rendered.append(content)
        else:
            rendered.append(repr(message))
    return rendered


app = FastAPI(title="Trip Planner API", version="0.1.0")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    bundle = get_workflow_bundle()
    await bundle.close()


@app.post("/plan", response_model=PlanResponse)
async def generate_plan(payload: PlanRequest) -> PlanResponse:
    bundle = get_workflow_bundle()
    try:
        thread_id, state = await bundle.plan_trip(
            context=payload.context,
            user_prompt=payload.user_prompt,
            thread_id=payload.thread_id,
        )
    except RuntimeError as exc:  # configuration issues
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    final_plan = state.final_plan
    status = "complete"
    next_plan = None
    if final_plan and final_plan.research_plan:
        status = "needs_follow_up"
        next_plan = final_plan.research_plan
    elif final_plan is None:
        status = "no_plan"

    return PlanResponse(
        thread_id=thread_id,
        status=status,
        final_plan=final_plan,
        next_research_plan=next_plan,
        messages=_state_messages_to_strings(state),
    )


@app.post("/plan/start", response_model=InterruptResponse)
async def start_planning_with_interrupt(payload: PlanRequest) -> InterruptResponse:
    """
    Start trip planning workflow that will pause at interrupt points for human review.
    
    This endpoint runs the workflow until it reaches a human review point,
    then returns the current state and interrupt data for user decision.
    """
    bundle = get_workflow_bundle()
    try:
        # Create thread ID if not provided
        thread_id = payload.thread_id or str(uuid4())
        
        # Set up configuration for interrupt handling
        config = {
            "recursion_limit": 100,
            "configurable": {"thread_id": thread_id}
        }
        
        # Create initial state
        initial_state = State(messages=[], estimated_budget=None, research_plan=None)
        
        # Run workflow until interrupt
        result = await bundle.graph.ainvoke(
            initial_state, 
            config=config, 
            context=payload.context
        )
        
        # Check if we hit an interrupt
        if "__interrupt__" in result:
            interrupt_data = result["__interrupt__"][0].value
            
            return InterruptResponse(
                thread_id=thread_id,
                status="interrupt",
                estimated_budget=result.get("estimated_budget"),
                research_plan=result.get("research_plan"),
                lodging=result.get("lodging"),
                activities=result.get("activities"),
                food=result.get("food"),
                intercity_transport=result.get("intercity_transport"),
                recommendations=result.get("recommendations"),
                interrupt_data=interrupt_data,
                messages=_state_messages_to_strings(result),
            )
        else:
            # No interrupt - workflow completed
            final_plan = result.get("final_plan")
            status = "complete" if final_plan else "no_plan"
            
            return InterruptResponse(
                thread_id=thread_id,
                status=status,
                estimated_budget=result.get("estimated_budget"),
                research_plan=result.get("research_plan"),
                lodging=result.get("lodging"),
                activities=result.get("activities"),
                food=result.get("food"),
                intercity_transport=result.get("intercity_transport"),
                recommendations=result.get("recommendations"),
                final_plan=final_plan,
                messages=_state_messages_to_strings(result),
            )
            
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/plan/resume", response_model=PlanResponse)
async def resume_planning_after_interrupt(payload: ResumeRequest) -> PlanResponse:
    """
    Resume trip planning workflow after human review selections.
    
    This endpoint continues the workflow from the interrupt point using
    the human selections provided in the request.
    """
    bundle = get_workflow_bundle()
    try:
        # Set up configuration
        config = {
            "recursion_limit": 100,
            "configurable": {"thread_id": payload.thread_id}
        }
        
        # Create resume command with human selections
        from langgraph.types import Command
        resume_command = Command(resume=payload.human_selections)
        
        # Resume workflow execution
        result = await bundle.graph.ainvoke(resume_command, config=config)
        
        # Check if workflow completed or hit another interrupt
        if "__interrupt__" in result:
            interrupt_data = result["__interrupt__"][0].value
            
            return PlanResponse(
                thread_id=payload.thread_id,
                status="interrupt",
                messages=_state_messages_to_strings(result),
            )
        else:
            # Workflow completed
            final_plan = result.get("final_plan")
            status = "complete" if final_plan else "no_plan"
            next_plan = None
            if final_plan and final_plan.research_plan:
                status = "needs_follow_up"
                next_plan = final_plan.research_plan
            
            return PlanResponse(
                thread_id=payload.thread_id,
                status=status,
                final_plan=final_plan,
                next_research_plan=next_plan,
                messages=_state_messages_to_strings(result),
            )
            
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health_check():
    """Health check endpoint to verify API is running."""
    return {"status": "healthy", "service": "trip-planner-api"}
