"""FastAPI surface for the trip planner agentic workflow."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env file before any other imports that might need environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

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
    CandidateLodging,
    CandidateIntercityTransport,
    CandidateActivity,
    CandidateFood,
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


class ResumeSelections(BaseModel):
    """Indices of options chosen during human-in-the-loop review."""

    lodging: Optional[int] = Field(
        default=None,
        description="Index of the selected lodging option (0-based).",
    )
    intercity_transport: Optional[int] = Field(
        default=None,
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
    research_plan: Optional[ResearchPlan] = Field(
        default=None,
        description="Optional overrides for the next research plan. Keys align with CandidateResearch fields.",
    )
    context: Optional[Context] = Field(
        ..., description="Context of the trip being planned.(Specify only if you didn't plan the trip before)"
    )


class PlanningResponse(BaseModel):
    """Unified response returned by both the start and resume endpoints."""

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
    lodging: Optional[List[CandidateLodging]] = Field(
        default=None, description="Candidate lodging options surfaced by the agent"
    )
    activities: Optional[List[CandidateActivity]] = Field(
        default=None, description="Candidate activities surfaced by the agent"
    )
    food: Optional[List[CandidateFood]] = Field(
        default=None, description="Candidate food options surfaced by the agent"
    )
    intercity_transport: Optional[List[CandidateIntercityTransport]] = Field(
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
            f"Missing required environment variables for planner workflow: {joined}"
        )


class WorkflowBundle:
    """Container for the LangGraph workflow and its dependencies.
    
    This class manages the complete trip planning workflow including:
    - LangGraph workflow compilation and execution
    - Research agent initialization and coordination
    - Thread state management for human-in-the-loop interactions
    - External service integrations (TripAdvisor, Amadeus, etc.)
    - Retrieval-augmented generation pipeline
    
    The workflow supports interrupt/resume functionality where users can make
    selections during the planning process and the workflow continues from
    that point.
    
    Attributes:
        settings: API configuration with external service credentials
        llm: Language model for agent reasoning and content generation
        agents: Specialized research agents for different travel categories
        graph: Compiled LangGraph workflow ready for execution
        recursion_limit: Maximum number of graph execution steps
        _contexts: Thread-specific context storage for resume functionality
        _configs: Thread-specific LangGraph configurations
        _pending_states: Workflow state storage for interrupted threads
        _pending_interrupts: User selection data for interrupted threads
    """

    def __init__(self, settings: ApiSettings) -> None:
        """Initialize the workflow bundle with all necessary components.
        
        Args:
            settings: Configuration containing API keys and service settings
        """
        _ensure_configuration(settings)
        settings.apply_langsmith_tracing()  

        self.settings = settings
        self.recursion_limit = DEFAULT_RECURSION_LIMIT

        self.llm = ChatXAI(
            model="grok-4-fast-reasoning",
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
        """Build the RAG pipeline for document retrieval and reranking.
        
        Returns:
            Configured RetrievalPipeline with OpenAI embeddings and FAISS vector store
        """
        config = RetrievalConfig(openai_api_key=self.settings.ensure("openai_api_key"))
        return create_default_pipeline(config)

    def _make_config(self, thread_id: str) -> Dict[str, Any]:
        """Create LangGraph configuration for a specific thread.
        
        Args:
            thread_id: Unique identifier for the planning thread
            
        Returns:
            LangGraph configuration dictionary with recursion limit and thread ID
        """
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
        payload: Dict[str, Any] = {}
        if state is None:
            # No pending state - this is a fresh start with selections/research_plan
            # Return an empty payload that represents starting with the given parameters

            if research_plan:
                payload["research_plan"] = research_plan.model_dump(exclude_none=True)
            
            # For fresh starts, we don't need to resolve existing options
            # Just return the research plan if provided
            return payload

        if research_plan:
            payload["research_plan"] = research_plan.model_dump(exclude_none=True)

        def resolve_options(key: str) -> List[Any]: 
            """Extract candidate options from stored agent output.
            
            Args:
                key: State key (e.g., 'lodging', 'activities')
                attr: Attribute name on the agent output (e.g., 'lodging', 'activities')
                
            Returns:
                List of candidate objects from the agent output
            """
            output = state.get(key)
            if output is None:
                return []
            # options = getattr(output, attr, None)
            return list(output)

        # Process single selections (lodging, transport) - user picks one option
        # single_map = {
        #     "lodging": ("lodging", selections.lodging),
        #     "intercity_transport": ("transport", selections.intercity_transport),
        # }
        single_map = {
            "lodging": selections.lodging, 
            "intercity_transport": selections.intercity_transport
        }
        # for key, (attr, index) in single_map.items():
        #     if index is None:
        #         continue
        #     options = resolve_options(key, attr)
        #     if not options:
        #         raise RuntimeError(f"No options stored for '{key}' to select from.")
        #     if index < 0 or index >= len(options):
        #         raise RuntimeError(f"Selection index {index} is out of range for '{key}'.")
        #     # Convert selected option to dictionary for LangGraph processing
        #     payload[key] = options[index].model_dump(exclude_none=True)

        for key, index in single_map.items():
            if index is None:
                continue
            options = resolve_options(key)
            if not options:
                raise RuntimeError(f"No options stored for '{key}' to select from.")
            if index < 0 or index >= len(options):
                raise RuntimeError(f"Selection index {index} is out of range for '{key}'.")
            # Convert selected option to dictionary for LangGraph processing
            payload[key] = options[index].model_dump(exclude_none=True)

        # Process multi-selections (activities, food) - user can pick multiple options
        multi_map = {
            "activities": selections.activities,
            "food":selections.food,
        }
        # for key, (attr, indices) in multi_map.items():
        #     if indices is None:
        #         continue
        #     options = resolve_options(key, attr)
        #     if not options:
        #         raise RuntimeError(f"No options stored for '{key}' to select from.")
            
        #     if indices:
        #         # User selected specific indices - filter to those options
        #         selected = []
        #         for idx in indices:
        #             if idx < 0 or idx >= len(options):
        #                 raise RuntimeError(
        #                     f"Selection index {idx} is out of range for '{key}'."
        #                 )
        #             selected.append(options[idx])
        #     else:
        #         # No specific selections - include all options
        #         selected = options
            
        #     # Convert all selected options to dictionaries for LangGraph processing
        #     dumps = [item.model_dump(exclude_none=True) for item in selected]
        #     payload[key] = dumps[0] if len(dumps) == 1 else dumps
        for key, indices in multi_map.items():
            if indices is None:
                continue
            options = resolve_options(key)
            if not options:
                raise RuntimeError(f"No options stored for '{key}' to select from.")
            selected = []
            if indices:
                for idx in indices:
                    if idx < 0 or idx >= len(options):
                        raise RuntimeError(f"Selection index {idx} is out of range for '{key}'.")
                    selected.append(options[idx])
      
            dumps = [item.model_dump(exclude_none=True) for item in selected]
            payload[key] = dumps

        return payload

    async def close(self) -> None:
        await self.trip_client.aclose()

    async def plan_trip(
        self,
        *,
        context: Context
    ) -> Tuple[str, Dict[str, Any], Mapping[str, Any]]:
        """Start a new trip planning workflow.
        
        This method initiates the complete trip planning process by:
        1. Creating a unique thread ID for this planning session
        2. Setting up LangGraph configuration and state storage
        3. Executing the workflow until completion or human interrupt
        4. Storing results for potential resume operations
        
        Args:
            context: Trip planning context containing destination, dates, budget,
                    traveller information, and trip preferences
                    
        Returns:
            Tuple containing:
            - thread_id: Unique identifier for this planning session
            - config: LangGraph configuration for resuming if interrupted
            - result: Workflow execution results including agent outputs and state
            
        Raises:
            RuntimeError: If workflow execution fails or encounters errors
        """
        active_thread = f"trip_{uuid4()}"
        config = self._configs.get(active_thread) or self._make_config(active_thread)

        self._contexts[active_thread] = context
        self._configs[active_thread] = config
        self._pending_states.pop(active_thread, None)
        self._pending_interrupts.pop(active_thread, None)

        messages: List[BaseMessage] = []
      
        initial_state = State(messages=messages)

        result = await self.graph.ainvoke(
            initial_state,
            context=context,
            config=config,
        )
        self._store_result(active_thread, result)
        return config, result

    async def resume_trip(
        self,
        *,
        context: Context,
        config: Optional[Dict[str, Any]],
        selections: ResumeSelections,
        research_plan: Optional[Dict[str, CandidateResearch]],
    ) -> Tuple[Dict[str, Any], Mapping[str, Any]]:
        """Resume a previously interrupted trip planning workflow.
        
        This method continues the planning process from where it was interrupted,
        incorporating user selections and optionally updating the research plan.
        It supports both resuming existing threads and starting fresh with selections.
        
        Args:
            context: Trip planning context (used for new threads when config is None)
            config: LangGraph configuration from previous interrupt (None for fresh start)
            selections: User choices for lodging, activities, food, and transport
            research_plan: Optional overrides for research parameters
            
        Returns:
            Tuple containing:
            - config: Updated LangGraph configuration with thread ID
            - result: Workflow execution results after resume
            
        Raises:
            RuntimeError: If thread_id is invalid or workflow execution fails
            
        Note:
            - If config is None, creates a new thread and stores context
            - Thread state is restored from _pending_states for existing threads
            - Selections are applied to filter candidate options
        """
        thread_id = None
        if config:
            configurable = config.get("configurable", {})
            thread_id = configurable.get("thread_id")

        if not thread_id:
            raise RuntimeError("Resume config must include configurable.thread_id.")

        if thread_id not in self._contexts:
            raise RuntimeError(f"Unknown planning thread '{thread_id}'.")
        else:
            thread_id = f"trip_{uuid4()}"
            # Store context for new thread when config is not provided
            self._contexts[thread_id] = context
            # Clear any existing state for this thread
            self._pending_states.pop(thread_id, None)
            self._pending_interrupts.pop(thread_id, None)
    
        active_config = config or self._make_config(thread_id)
        self._configs[thread_id] = active_config

        resume_payload = self._build_resume_payload(
            thread_id=thread_id,
            selections=selections,
            research_plan=research_plan,
        )

        command = Command(resume=resume_payload)
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
    config: Dict[str, Any],
    result: Mapping[str, Any],
) -> PlanningResponse:
    status = _determine_status(result)
    interrupt_payload = _extract_interrupt(result)

    # Extract lodging list from nested structure
    lodging_data = result.get("lodging")
    lodging_list = None
    if lodging_data and hasattr(lodging_data, 'lodging'):
        lodging_list = lodging_data.lodging
    elif lodging_data and isinstance(lodging_data, dict) and 'lodging' in lodging_data:
        lodging_list = lodging_data['lodging']
    elif lodging_data and isinstance(lodging_data, list):
        lodging_list = lodging_data

    # Extract activities list from nested structure
    activities_data = result.get("activities")
    activities_list = None
    if activities_data and hasattr(activities_data, 'activities'):
        activities_list = activities_data.activities
    elif activities_data and isinstance(activities_data, dict) and 'activities' in activities_data:
        activities_list = activities_data['activities']
    elif activities_data and isinstance(activities_data, list):
        activities_list = activities_data

    # Extract food list from nested structure
    food_data = result.get("food")
    food_list = None
    if food_data and hasattr(food_data, 'food'):
        food_list = food_data.food
    elif food_data and isinstance(food_data, dict) and 'food' in food_data:
        food_list = food_data['food']
    elif food_data and isinstance(food_data, list):
        food_list = food_data

    # Extract intercity_transport list from nested structure
    transport_data = result.get("intercity_transport")
    transport_list = None
    if transport_data and hasattr(transport_data, 'transport'):
        transport_list = transport_data.transport
    elif transport_data and isinstance(transport_data, dict) and 'transport' in transport_data:
        transport_list = transport_data['transport']
    elif transport_data and isinstance(transport_data, list):
        transport_list = transport_data

    return PlanningResponse(    
        status=status,
        config=config,
        estimated_budget=result.get("estimated_budget"),
        research_plan=result.get("research_plan"),
        lodging=lodging_list,
        activities=activities_list,
        food=food_list,
        intercity_transport=transport_list,
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
    """Start the AI-powered trip planning workflow.
    
    This endpoint initiates the LangGraph-based trip planning process that coordinates
    multiple specialized agents to research and create a personalized itinerary.
    
    The workflow includes:
    - Budget estimation based on destination and travel dates
    - Research planning to determine candidate counts for each category
    - Parallel research by specialized agents (lodging, activities, food, transport)
    - Human-in-the-loop selection process when multiple options are found
    - Final itinerary synthesis
    
    Args:
        payload: Contains the trip context including destination, dates, budget,
                traveller information, and optional thread_id and user_prompt.
                
    Returns:
        PlanningResponse containing:
        - status: Current workflow state ("interrupt", "complete", "needs_follow_up", "no_plan")
        - config: LangGraph configuration with thread_id for resuming
        - estimated_budget: AI-generated budget breakdown by category
        - research_plan: Research strategy for each category
        - agent_outputs: Results from research agents (lodging, activities, etc.)
        - interrupt: Selection options when status is "interrupt"
        - final_plan: Complete itinerary when status is "complete"
        
    Raises:
        HTTPException: 400 for invalid input, 500 for workflow errors
        
    Example:
        POST /plan/start with:
        ```json
        {
            "context": {
                "destination": "Tokyo, Japan",
                "date_from": "2025-10-01",
                "date_to": "2025-10-05",
                "budget": 1000,
                "currency": "USD",
                "group_type": "alone",
                "travellers": [{"name": "John", "date_of_birth": "1990-01-01"}]
            }
        }
        ```
    ```json
        {
            "context": 
            {
                "travellers": [
                {
                    "name": "Danil",
                    "date_of_birth": "2002-09-29",
                    "spoken_languages": [
                    "english"
                    ],
                    "interests": [
                    "active sports"
                    ],
                    "nationality": "russian"      }
                ],
                "budget": 1000,
                "currency": "USD",
                "destination": "Tokyo",
                "destination_country": "Japan",
                "date_from": "2025-10-01",
                "date_to": "2025-10-05",
                "group_type": "alone",
                "trip_purpose": "cultural experience",
                "current_location": "Seoul"
            }
        }
    ```
    """

    logger.info("Starting new trip planning request")
    logger.info(f"Destination: {payload.context.destination}, {payload.context.destination_country}")
    logger.info(f"Budget: {payload.context.budget} {payload.context.currency}")
    logger.info(f"Travel dates: {payload.context.date_from} to {payload.context.date_to}")
    logger.info(f"Group size: {payload.context.adults_num} adults, {payload.context.children_num} children")
    
    bundle = get_workflow_bundle()
    try:
        config, result = await bundle.plan_trip(
            context=payload.context
        )
        logger.info("Plan_trip workflow completed successfully")
        logger.debug(f"Result keys: {list(result.keys()) if result else 'None'}")
        logger.info("Converting result to response")
    except RuntimeError as exc:
        logger.error(f"Runtime error during plan: {str(exc)}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safeguards unexpected graph failures
        logger.error(f"Unexpected error during plan: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _result_to_response(config, result)
    

@app.post("/plan/resume", response_model=PlanningResponse)
async def resume_planning(payload: ResumeRequest) -> PlanningResponse:
    """Resume the trip planning workflow after user selections.
    
    This endpoint continues the planning workflow from where it was interrupted,
    incorporating user selections for lodging, activities, food, and transport options.
    The workflow will proceed to generate the final itinerary or request additional
    selections if needed.
    
    The resume process:
    - Uses the provided config to restore the workflow state
    - Applies user selections to filter down to chosen options
    - Continues with final planning and itinerary generation
    - Can handle research plan overrides for additional research
    
    Args:
        payload: Contains:
            - config: LangGraph configuration with thread_id from previous response
            - selections: User choices for each category (indices or objects)
            - research_plan: Optional overrides for additional research
            
    Returns:
        PlanningResponse with updated workflow state:
        - status: "interrupt" for more selections needed, "complete" for final plan
        - final_plan: Complete day-by-day itinerary when status is "complete"
        - Additional agent outputs and selections as needed
        
    Raises:
        HTTPException: 400 for invalid thread_id or selections, 500 for workflow errors
        
    Note:
        - If config is None, creates a new planning session with provided selections
        - Selections can be indices (integers) or full candidate objects
        - Research plan overrides allow requesting additional candidates
        
    Example:
        POST /plan/resume with:
        ```json
        {
            "config": {"configurable": {"thread_id": "trip_123"}},
            "selections": {
                "lodging": 0,
                "activities": [0, 1, 2],
                "food": [0, 1],
                "intercity_transport": 0
            }
        }
        ```
    
    Example input:
    ```json
    {
        "selections": {
            "lodging": {
      "id": null,
      "name": "Khaosan Tokyo Samurai Hostel",
      "address": "1-11-4 Asakusa, Taito-ku, Tokyo",
      "price_level": "$",
                "rating": 4.5,
      "reviews": [
        "Great location near temple",
        "Clean and affordable for solo travelers"
      ],
      "photos": [
        "https://example.com/photo1.jpg"
      ],
      "url": "https://www.tripadvisor.com/Hotel_Review-g14134310-d1234567-Reviews-Khaosan_Tokyo_Samurai_Hostel-Asakusa_Taito_Tokyo_Tokyo_Prefecture_Kanto.html",
      "lat": 35.7148,
      "lon": 139.7967,
                "evidence_score": 0.9,
      "source_id": "tripadvisor",
      "notes": "Near Sumida Park for sports",
      "area": "Asakusa",
      "price_night": 55,
      "cancel_policy": "Free cancellation up to 48 hours"
            },
            "activities": [
                {
        "id": null,
        "name": "Senso-ji Temple Walk and Asakusa Exploration",
                    "address": "2-3-1 Asakusa, Taito City, Tokyo",
                    "price_level": "$",
        "rating": 4.5,
        "reviews": [
          "Iconic temple with vibrant street atmosphere",
          "Great for walking and photos"
        ],
        "photos": [
          "https://example.com/sensoji1.jpg"
        ],
        "url": "https://www.tripadvisor.com/Attraction_Review-g14134310-d320531-Reviews-Senso_ji_Temple-Asakusa_Taito_Tokyo_Tokyo_Prefecture_Kanto.html",
                    "lat": 35.7148,
                    "lon": 139.7967,
                    "evidence_score": 0.9,
        "source_id": "tripadvisor",
        "notes": "Free cultural walking activity with active elements",
        "open_time": "06:00",
        "close_time": "17:00",
        "duration_min": 120,
        "price": 0,
        "tags": [
          "cultural",
          "walking",
          "free"
        ]
      },
      {
        "id": null,
        "name": "Yoyogi Park Jogging and Meiji Shrine Visit",
        "address": "2-2-1 Yoyogi-Kamizonocho, Shibuya City, Tokyo",
        "price_level": "$",
        "rating": 4.6,
        "reviews": [
          "Perfect for morning jogs and peaceful shrine walks",
          "Solo-friendly green space"
        ],
        "photos": [
          "https://example.com/yoyogi1.jpg"
        ],
        "url": "https://www.tripadvisor.com/Attraction_Review-g1066456-d320609-Reviews-Yoyogi_Park-Yoyogi_Shibuya_Tokyo_Tokyo_Prefecture_Kanto.html",
        "lat": 35.6699,
        "lon": 139.6917,
        "evidence_score": 0.85,
        "source_id": "tripadvisor",
        "notes": "Active sports in park combined with cultural shrine",
        "open_time": "05:00",
        "close_time": "20:00",
        "duration_min": 120,
        "price": 0,
        "tags": [
          "active sports",
          "cultural",
          "free"
        ]
      },
      {
        "id": null,
        "name": "Ueno Park Cycling and Museum Hopping",
        "address": "5-20 Uenokoen, Taito City, Tokyo",
        "price_level": "$$",
        "rating": 4.4,
        "reviews": [
          "Rent bikes for fun exploration",
          "Cultural museums nearby at low cost"
        ],
        "photos": [
          "https://example.com/ueno1.jpg"
        ],
        "url": "https://www.tripadvisor.com/Attraction_Review-g1066449-d320583-Reviews-Ueno_Park-Ueno_Taito_Tokyo_Tokyo_Prefecture_Kanto.html",
        "lat": 35.7137,
        "lon": 139.7719,
        "evidence_score": 0.8,
        "source_id": "tripadvisor",
        "notes": "Cycling for active sports, cultural park and museums",
        "open_time": "05:00",
        "close_time": "18:00",
        "duration_min": 180,
        "price": 10,
        "tags": [
          "cycling",
          "cultural",
          "park"
        ]
      },
      {
        "id": null,
        "name": "Shinjuku Gyoen National Garden Hike",
        "address": "11 Naitomachi, Shinjuku City, Tokyo",
        "price_level": "$",
        "rating": 4.7,
        "reviews": [
          "Beautiful gardens for hiking and relaxation",
          "Cultural Japanese landscape"
        ],
        "photos": [
          "https://example.com/shinjuku1.jpg"
        ],
        "url": "https://www.tripadvisor.com/Attraction_Review-g1066455-d320599-Reviews-Shinjuku_Gyoen_National_Garden-Shinjuku_Tokyo_Tokyo_Prefecture_Kanto.html",
        "lat": 35.6869,
        "lon": 139.7193,
        "evidence_score": 0.95,
        "source_id": "tripadvisor",
        "notes": "Moderate hike in cultural garden setting",
        "open_time": "09:00",
        "close_time": "16:00",
        "duration_min": 120,
        "price": 5,
        "tags": [
          "hiking",
          "cultural",
          "garden"
        ]
                }
            ],
            "food": [
                {
        "id": null,
        "name": "Tsukiji Outer Market Stalls",
        "address": "4 Chome-16-2 Tsukiji, Chuo City, Tokyo 104-0045, Japan",
        "price_level": "$",
        "rating": 4.5,
        "reviews": [
          "Fresh and authentic seafood experience.",
          "Great for solo travelers."
        ],
        "photos": [
          "https://example.com/tsukiji1.jpg"
        ],
        "url": "https://www.tripadvisor.com/Attraction_Review-g14129574-d320669-Reviews-Tsukiji_Outer_Market-Tsukiji_Chuo_Tokyo_Tokyo_Prefecture_Kanto.html",
        "lat": 35.6666,
        "lon": 139.7661,
        "evidence_score": 0.9,
        "source_id": null,
        "notes": "Street food for cultural immersion.",
        "open_time": "08:00",
        "close_time": "18:00",
        "tags": [
          "street food",
          "japanese",
          "seafood"
        ]
      },
      {
        "id": null,
        "name": "Omoide Yokocho Yakitori",
        "address": "1 Chome-2 Nishishinjuku, Shinjuku City, Tokyo 160-0023, Japan",
        "price_level": "$",
        "rating": 4,
        "reviews": [
          "Lively alley with grilled skewers.",
          "Affordable and authentic."
        ],
        "photos": [
          "https://example.com/omoide1.jpg"
        ],
        "url": "https://www.tripadvisor.com/Attraction_Review-g1066456-d324986-Reviews-Omoide_Yokocho-Shinjuku_Tokyo_Tokyo_Prefecture_Kanto.html",
        "lat": 35.6911,
        "lon": 139.7005,
        "evidence_score": 0.85,
        "source_id": null,
        "notes": "Solo-friendly izakaya vibe.",
        "open_time": "17:00",
        "close_time": "23:00",
        "tags": [
          "yakitori",
          "street food",
          "local"
        ]
      },
      {
        "id": null,
        "name": "Ichiran Ramen (Shinjuku Branch)",
        "address": "1-21-1 Kabukicho, Shinjuku City, Tokyo 160-0021, Japan",
        "price_level": "$",
                    "rating": 4.2,
        "reviews": [
          "Customizable ramen ritual.",
          "Perfect for one person."
        ],
        "photos": [
          "https://example.com/ichiran1.jpg"
        ],
        "url": "https://www.tripadvisor.com/Restaurant_Review-g1066456-d1665415-Reviews-Ichiran_Shinjuku-Shinjuku_Tokyo_Tokyo_Prefecture_Kanto.html",
        "lat": 35.6895,
        "lon": 139.6987,
        "evidence_score": 0.95,
        "source_id": null,
        "notes": "Budget tonkotsu ramen.",
        "open_time": "10:00",
        "close_time": "02:00",
        "tags": [
          "ramen",
          "japanese",
          "chain"
        ]
      }
    ],
    "intercity_transport": {
      "name": "Jeju Air Direct Flight",
      "fare_class": null,
      "refundable": null,
      "url": null,
      "price": 220,
      "transfer": [
        {
          "name": "Flight",
          "place": "Seoul (ICN) to Tokyo (NRT)",
          "departure_time": "09:00",
          "arrival_time": "11:30",
          "duration_min": 150
        },
        {
          "name": "Flight",
          "place": "Tokyo (NRT) to Seoul (ICN)",
          "departure_time": "12:00",
          "arrival_time": "14:30",
          "duration_min": 150
        }
      ],
      "total_duration_min": 300,
      "note": "Round-trip budget option, direct flights on Oct 1 and Oct 5, 2025. Fits 300 USD budget."
    }
        },
        "research_plan": {
    "food_candidates": {
      "name": "restaurants",
      "description": "traditional restaurants",
      "candidates_number": 2
    }
  },
    "context": 
            {
                "travellers": [
                {
                    "name": "Danil",
                    "date_of_birth": "2002-09-29",
                    "spoken_languages": [
                    "english"
                    ],
                    "interests": [
                    "active sports"
                    ],
                    "nationality": "russian"      }
                ],
                "budget": 1000,
                "currency": "USD",
                "destination": "Tokyo",
                "destination_country": "Japan",
                "date_from": "2025-10-01",
                "date_to": "2025-10-05",
                "group_type": "alone",
                "trip_purpose": "cultural experience",
                "current_location": "Seoul"
        }
    }
    ```
    """

    logger.info("Resume planning request received")
    logger.debug(f"Payload config: {payload.config}")
    logger.debug(f"Payload selections: {payload.selections}")
    logger.debug(f"Payload research_plan: {payload.research_plan}")

    bundle = get_workflow_bundle()
    try:
        logger.info("Starting resume_trip workflow")
        config, result = await bundle.resume_trip(
            context=payload.context,
            config=payload.config,
            selections=payload.selections,
            research_plan=payload.research_plan,
        )
        logger.info("Resume_trip workflow completed successfully")
        logger.debug(f"Result: {result}")

    except RuntimeError as exc:
        logger.error(f"Runtime error during resume: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safeguards unexpected graph failures
        logger.error(f"Unexpected error during resume: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Converting result to response")
    response = _result_to_response(config, result)
    logger.info("Resume planning completed successfully")
    return response  


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health endpoint used for readiness probes."""

    return {"status": "healthy", "service": "trip-planner-api"}
