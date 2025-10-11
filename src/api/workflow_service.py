from src.core.config import ApiSettings
from src.services import (
    create_amadeus_client,
    create_flight_search_tool,
    create_trip_advisor_client,
    create_trip_advisor_tools,
    create_internet_tool,
    create_reddit_tool,
)
from src.workflows.planner import build_research_agents, build_research_graph
from src.api.schemas import ResumeSelections
from langchain_core.messages import BaseMessage
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
from typing import Dict, Any, List, Optional, Tuple, Mapping
import os
from uuid import uuid4
from src.pipelines.rag import RetrievalConfig, RetrievalPipeline, create_default_pipeline
from src.core.domain import (
    CandidateResearch,
    Context,
    State,
)
from langchain_xai import ChatXAI


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
            comprehensive_search_tool=self.trip_tools,
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

    def __repr__(self) -> str:
    
        llm_name = getattr(self.llm, 'model_name', None) or getattr(self.llm, 'model', None) or type(self.llm).__name__
        
        return (
            f"WorkflowBundle(\n"
            f"  llm='{llm_name}',\n"
            f"  recursion_limit={self.recursion_limit},\n"
            f"  agents={{\n"
            f"    lodging={type(self.agents.lodging).__name__},\n"
            f"    activities={type(self.agents.activities).__name__},\n"
            f"    food={type(self.agents.food).__name__},\n"
            f"    intercity_transport={type(self.agents.intercity_transport).__name__},\n"
            f"    recommendations={type(self.agents.recommendations).__name__}\n"
            f"  }},\n"
            f"  services={{\n"
            f"    trip_advisor={type(self.trip_client).__name__},\n"
            f"    flight_search={type(self.flight_client).__name__},\n"
            f"    retrieval_pipeline={type(self.retrieval_pipeline).__name__}\n"
            f"  }},\n"
            f"  graph_compiled={self.graph is not None},\n"
            f"  active_threads={len(self._contexts)},\n"
            f"  pending_interrupts={len(self._pending_interrupts)}\n"
            f")"
        )

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

    def get_thread_context(self, thread_id: str) -> Optional[Context]:
        """Return the stored planning context for a thread, if present."""

        return self._contexts.get(thread_id)

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
            """Extract candidate options from stored agent output."""
            output = state.get(key)
            if output is None:
                return []
            
            # Extract the list field from the agent output
            # e.g., LodgingAgentOutput has a .lodging field
            if hasattr(output, key):
                return getattr(output, key) or []
            
            return []


        single_map = {
            "lodging": selections.lodging, 
            "intercity_transport": selections.intercity_transport
        }

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
        context: Optional[Context]=None,
        config: Dict[str, Any],
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
      
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")

        if not thread_id:
            raise RuntimeError("Resume config must include configurable.thread_id.")

        if thread_id not in self._contexts:
            raise RuntimeError(f"Unknown planning thread '{thread_id}'.")

        stored_context = self._contexts[thread_id]
        execution_context = context or stored_context

        if execution_context is None:
            raise RuntimeError(f"No planning context available for thread '{thread_id}'.")

        if context is not None:
            self._contexts[thread_id] = context

        active_config = config or self._make_config(thread_id)
        self._configs[thread_id] = active_config

        resume_payload = self._build_resume_payload(
            thread_id=thread_id,
            selections=selections,
            research_plan=research_plan,
        )

        command = Command(resume=resume_payload)
        result = await self.graph.ainvoke(
            command,
            context=execution_context,
            config=active_config,
        )
        self._store_result(thread_id, result)

        return active_config, result

