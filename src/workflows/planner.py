"""LangGraph workflow assembly extracted from the notebook."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

from langchain.agents import AgentExecutor
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import Tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from src.core.domain import (
    ActivitiesAgentOutput,
    BudgetEstimate,
    CandidateIntercityTransport,
    CandidateLodging,
    Context,
    FinalPlan,
    FoodAgentOutput,
    IntercityTransportAgentOutput,
    LodgingAgentOutput,
    RecommendationsOutput,
    ResearchPlan,
    State,
)
from src.services.geocoding import get_coordinates_nominatim


@dataclass(slots=True)
class ResearchAgents:
    """Container for the task-specific research agents."""

    lodging: AgentExecutor
    activities: AgentExecutor
    food: AgentExecutor
    intercity_transport: AgentExecutor
    recommendations: AgentExecutor


def build_research_agents(
    llm: BaseChatModel,
    *,
    comprehensive_search_tool: Tool,
    flight_search_tool: Tool,
    search_tools: Sequence[Tool],
) -> ResearchAgents:
    """Instantiate the REACT agents required by the workflow."""

    from langgraph.prebuilt import create_react_agent

    return ResearchAgents(
        lodging=create_react_agent(
            llm,
            tools=[comprehensive_search_tool],
            response_format=LodgingAgentOutput,
        ),
        activities=create_react_agent(
            llm,
            tools=[comprehensive_search_tool],
            response_format=ActivitiesAgentOutput,
        ),
        food=create_react_agent(
            llm,
            tools=[comprehensive_search_tool],
            response_format=FoodAgentOutput,
        ),
        intercity_transport=create_react_agent(
            llm,
            tools=[flight_search_tool],
            response_format=IntercityTransportAgentOutput,
        ),
        recommendations=create_react_agent(
            llm,
            tools=list(search_tools),
            response_format=RecommendationsOutput,
        ),
    )


def make_budget_estimate_node(llm: BaseChatModel):
    """Return the budget estimation node bound to the provided LLM."""

    structured_llm = llm.with_structured_output(BudgetEstimate)

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        prompt = (
            "Create budget breakdown for {group} trip: {origin} → {destination}, {country}.\n"
            "{adults} adults, {children} children, {infants} infants.\n"
            "{days} days ({date_from} to {date_to}).\n"
            "Total budget: {budget} {currency}.\n"
            "Trip purpose: {purpose}\n"
            "Notes: {notes}"
        ).format(
            group=runtime.context.group_type,
            origin=runtime.context.current_location,
            destination=runtime.context.destination,
            country=runtime.context.destination_country,
            adults=runtime.context.adults_num,
            children=runtime.context.children_num,
            infants=runtime.context.infant_num,
            days=runtime.context.days_number,
            date_from=runtime.context.date_from,
            date_to=runtime.context.date_to,
            budget=runtime.context.budget,
            currency=runtime.context.currency,
            purpose=runtime.context.trip_purpose,
            notes=runtime.context.notes,
        )
        budget = await structured_llm.ainvoke(prompt)
        return {
            "messages": [
                AIMessage(
                    content=f"Estimated budget: {budget.model_dump_json()}",
                    name="budget_estimate",
                )
            ],
            "estimated_budget": budget,
        }

    return node


def make_research_plan_node(llm: BaseChatModel):
    """Return the research planning node bound to the LLM."""

    structured_llm = llm.with_structured_output(ResearchPlan)

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        prompt = (
            "Set candidate counts for travel research based on: {context}.\n"
            "Budget plan: {budget}\n"
            "Currency: {currency}.\n"
            "Longer trips need more options. Families need more lodging/food.\n"
            "Couples need more activities. Use whole numbers ≥ 0."
        ).format(
            context=runtime.context,
            budget=state.estimated_budget,
            currency=runtime.context.currency,
        )
        plan = await structured_llm.ainvoke(prompt)
        coordinates = get_coordinates_nominatim(
            f"{runtime.context.destination}, {runtime.context.destination_country}"
        )
        return {
            "messages": [
                AIMessage(
                    content=f"Research plan: {plan.model_dump_json()}",
                    name="research_plan",
                )
            ],
            "research_plan": plan,
            "destination_coordinates": coordinates,
        }

    return node


def _extract_agent_output(
    response: Dict[str, Any],
    *,
    key: str,
    default,
) -> Dict[str, Any]:
    """Normalise agent responses into the shared node contract."""

    payload = response.get("structured_response", default)
    messages = response.get("messages", [])
    return {"messages": messages, key: payload}


def make_lodging_node(agent: AgentExecutor):
    """Return an async node that orchestrates lodging research."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        candidates = state.research_plan.lodging_candidates if state.research_plan else None
        prompt = f"""
        You are a travel research assistant specializing in lodging.
        Use only provided documents and tools. Avoid fabricating data.

        [INPUT CONTEXT]
        {runtime.context}
        Budget (lodging total): {state.estimated_budget.lodging if state.estimated_budget else 'unknown'} {runtime.context.currency}

        Candidates research details: {candidates}
        Return only {candidates.candidates_number if candidates and candidates.candidates_number else 'the requested number of'} options.

        IMPORTANT: When creating lodging candidates, use the 'location_id' from the API responses as the 'id' field. 
       
        """
        response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        default = LodgingAgentOutput(lodging=[])
        return _extract_agent_output(response, key="lodging", default=default)

    return node


def make_activities_node(agent: AgentExecutor):
    """Create the activities research node used in the LangGraph flow."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        candidates = state.research_plan.activities_candidates if state.research_plan else None
        prompt = f"""
        You are a travel research assistant specializing in activities.
        Only use facts explicitly present in the documents.

        [INPUT CONTEXT]
        {runtime.context}
        Budget (activities total): {state.estimated_budget.activities if state.estimated_budget else 'unknown'} {runtime.context.currency}

        Candidates research details: {candidates}
        Return only {candidates.candidates_number if candidates and candidates.candidates_number else 'the requested number of'} options.

        IMPORTANT: When creating activity candidates, use the 'location_id' from the API responses as the 'id' field. 
        
        """
        response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        default = ActivitiesAgentOutput(activities=[])
        return _extract_agent_output(response, key="activities", default=default)

    return node


def make_food_node(agent: AgentExecutor):
    """Produce the food research node that queries the cuisine agent."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        candidates = state.research_plan.food_candidates if state.research_plan else None
        prompt = f"""
        You are a travel research assistant specializing in food & dining.
        Use only facts from provided documents.

        [INPUT CONTEXT]
        {runtime.context}
        Budget (food total): {state.estimated_budget.food if state.estimated_budget else 'unknown'} {runtime.context.currency}

        Candidates research details: {candidates}
        Return only {candidates.candidates_number if candidates and candidates.candidates_number else 'the requested number of'} options.

        IMPORTANT: When creating food candidates, use the 'location_id' from the API responses as the 'id' field. 
       
        """
        response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        default = FoodAgentOutput(food=[])
        return _extract_agent_output(response, key="food", default=default)

    return node


def make_intercity_transport_node(agent: AgentExecutor):
    """Assemble the LangGraph node responsible for intercity transport."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        candidates = state.research_plan.intercity_transport_candidates if state.research_plan else None
        prompt = f"""
        You are a travel research assistant specializing in intercity transport.
        Only use facts from provided documents.

        [INPUT CONTEXT]
        {runtime.context}
        Budget (intercity transport total): {state.estimated_budget.intercity_transport if state.estimated_budget else 'unknown'} {runtime.context.currency}

        Candidates research details: {candidates}
        Return only {candidates.candidates_number if candidates and candidates.candidates_number else 'the requested number of'} options.
        """
        response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        default = IntercityTransportAgentOutput(transport=[])
        return _extract_agent_output(response, key="intercity_transport", default=default)

    return node


def make_recommendations_node(agent: AgentExecutor):
    """Build the advisory node that aggregates safety and culture notes."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        prompt = f"""
        You are a travel advisor providing safety, cultural, and practical recommendations.
        Only use facts from provided documents.

        [INPUT CONTEXT]
        {runtime.context}
        """
        response = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        default = RecommendationsOutput(
            safety_level="moderate", child_friendly_rating=3
        )
        return _extract_agent_output(response, key="recommendations", default=default)

    return node


def make_planner_node(llm: BaseChatModel):
    """Create the planner node that synthesises all research into a plan."""

    structured_llm = llm.with_structured_output(FinalPlan)

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        # Define the prompt
        prompt = f"""
        You are a Trip Planning Assistant.

        Your task:
        - Take the research results provided from other specialized agents
        - Synthesize them into a detailed, day-by-day, coherent, and optimized trip plan

        [INPUT CONTEXT]
        {state}
        {runtime.context}
        """
        planner = await structured_llm.ainvoke(prompt)

        return {
            "messages": [
                HumanMessage(content=f"Prompt: {prompt}", name="planner_prompt"),
                AIMessage(content=f"Final plan: {planner}", name="final_plan")
            ],
            "final_plan": planner,
        }

    return node


def make_combined_human_review_node():
    """Return a node that pauses execution to collect human selections."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        """Single node that handles both lodging and transport selection"""
        
        interrupts_needed = []

        if state.lodging and state.lodging.lodging:
            interrupts_needed.append({
                "type": "lodging",
                "task": "Choose lodging option",
                "options": [lodging.model_dump() for lodging in state.lodging.lodging]
            })

        if state.intercity_transport and state.intercity_transport.transport:
            interrupts_needed.append({
                "type": "intercity_transport",
                "task": "Choose intercity_transport option",
                "options": [transport.model_dump() for transport in state.intercity_transport.transport]
            })

        if state.activities and state.activities.activities:
            interrupts_needed.append({
                "type": "activities",
                "task": "Choose activity option",
                "options": [activity.model_dump() for activity in state.activities.activities]
            })

        if state.food and state.food.food:
            interrupts_needed.append({
                "type": "food",
                "task": "Choose food option",
                "options": [food.model_dump() for food in state.food.food]
            })

        if not interrupts_needed:
            return {}

        # Import interrupt RIGHT BEFORE using it to avoid namespace conflicts
        from langgraph.types import interrupt

        # This will either:
        # 1. Pause execution on first run (and store interrupt data)
        # 2. Return the resume data when resumed
        result = interrupt({
            "task": "Make your selections for the following options",
            "selections": interrupts_needed,
            "research_plan": state.research_plan.model_dump() if state.research_plan else None
        })

        # This code runs AFTER resume
        # Initialize response with a message
        from src.core.domain import CandidateActivity, CandidateFood
        
        response = {"messages": [HumanMessage(content="Human review completed")]}

        # Handle research_plan if it's in the result
        if "research_plan" in result and result["research_plan"]:
            from src.core.domain import CandidateResearch, ResearchPlan
            research_plan_dict = result["research_plan"]
            research_plan_data = {}

            # Convert each category to CandidateResearch objects
            for category_key, category_data in research_plan_dict.items():
                if category_data:
                    research_plan_data[category_key] = CandidateResearch(**category_data)

            # Create ResearchPlan and convert to dict for state update
            research_plan = ResearchPlan(**research_plan_data)
            response["research_plan"] = research_plan.model_dump()
        else:
            response["research_plan"] = None

        # Handle activities - could be single dict or list of dicts
        if "activities" in result and result["activities"]:
            activities_data = result["activities"]
            # Ensure it's a list
            if isinstance(activities_data, dict):
                activities_data = [activities_data]
            selected_activities = [CandidateActivity(**activity) for activity in activities_data]
            response["activities"] = ActivitiesAgentOutput(activities=selected_activities).model_dump()

        # Handle food - could be single dict or list of dicts
        if "food" in result and result["food"]:
            food_data = result["food"]
            # Ensure it's a list
            if isinstance(food_data, dict):
                food_data = [food_data]
            selected_foods = [CandidateFood(**food_item) for food_item in food_data]
            response["food"] = FoodAgentOutput(food=selected_foods).model_dump()

        # Handle lodging - expecting single dict but wrap in list for LodgingAgentOutput
        if "lodging" in result and result["lodging"]:
            lodging_data = result["lodging"]
            # Ensure it's a list for the output model
            if isinstance(lodging_data, dict):
                lodging_data = [lodging_data]
            selected_lodgings = [CandidateLodging(**lodging) for lodging in lodging_data]
            response["lodging"] = LodgingAgentOutput(lodging=selected_lodgings).model_dump()

        # Handle intercity_transport - expecting single dict but wrap in list for IntercityTransportAgentOutput
        if "intercity_transport" in result and result["intercity_transport"]:
            transport_data = result["intercity_transport"]
            # Ensure it's a list for the output model
            if isinstance(transport_data, dict):
                transport_data = [transport_data]
            selected_transport = [CandidateIntercityTransport(**transport) for transport in transport_data]
            response["intercity_transport"] = IntercityTransportAgentOutput(transport=selected_transport).model_dump()

        return response

    return node


def route_from_human_response(state: State, runtime: Runtime[Context]) -> Union[str, List[str]]:
    """Returns a list of nodes to execute in parallel based on conditions"""
    nodes_to_execute = []
    if not state.research_plan:
        return "planner"

    research_plan = state.research_plan

    # Direct attribute access (works if these are Optional[bool] fields)
    if research_plan.activities_candidates:
        nodes_to_execute.append("research_activities")

    if research_plan.food_candidates:
        nodes_to_execute.append("research_food")

    if research_plan.lodging_candidates:
        nodes_to_execute.append("research_lodging")

    if research_plan.intercity_transport_candidates:
        nodes_to_execute.append("research_intercity_transport")

    return nodes_to_execute if nodes_to_execute else "planner"


def build_research_graph(
    *,
    llm: BaseChatModel,
    agents: ResearchAgents,
    human_review: str = "auto",
    memory: Optional[InMemorySaver] = None,
) -> Any:
    """Wire all nodes into a compiled LangGraph state machine."""

    # Create all the nodes
    budget_estimate_node = make_budget_estimate_node(llm)
    research_plan_node = make_research_plan_node(llm)
    lodging_node = make_lodging_node(agents.lodging)
    activities_node = make_activities_node(agents.activities)
    food_node = make_food_node(agents.food)
    intercity_node = make_intercity_transport_node(agents.intercity_transport)
    recommendations_node = make_recommendations_node(agents.recommendations)
    human_review_node = make_combined_human_review_node()
    planner_node = make_planner_node(llm)

    graph_builder = StateGraph(state_schema=State, context_schema=Context)

    graph_builder.add_node("budget_estimate", budget_estimate_node)
    graph_builder.add_node("research_plan", research_plan_node)
    graph_builder.add_node("research_lodging", lodging_node)
    graph_builder.add_node("research_activities", activities_node)
    graph_builder.add_node("research_food", food_node)
    graph_builder.add_node("research_intercity_transport", intercity_node)
    graph_builder.add_node("research_recommendations", recommendations_node)
    graph_builder.add_node("combined_human_review", human_review_node)
    graph_builder.add_node("planner", planner_node)

    # Initial flow
    graph_builder.add_edge(START, "budget_estimate")
    graph_builder.add_edge("budget_estimate", "research_plan")

    # Parallel research
    graph_builder.add_edge("research_plan", "research_activities")
    graph_builder.add_edge("research_plan", "research_lodging")
    graph_builder.add_edge("research_plan", "research_food")
    graph_builder.add_edge("research_plan", "research_intercity_transport")
    graph_builder.add_edge("research_plan", "research_recommendations")

    graph_builder.add_edge("research_activities", "combined_human_review")
    graph_builder.add_edge("research_lodging", "combined_human_review")
    graph_builder.add_edge("research_food", "combined_human_review")
    graph_builder.add_edge("research_intercity_transport", "combined_human_review")
    graph_builder.add_edge("research_recommendations", "combined_human_review")

    graph_builder.add_conditional_edges("combined_human_review", path=route_from_human_response)

    # Then from combined_human_review to planner
    graph_builder.add_edge("planner", END)

    return graph_builder.compile(checkpointer=memory or InMemorySaver())
