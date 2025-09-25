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
    schema_info = json.dumps(FinalPlan.model_json_schema(), indent=2)

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        prompt = f"""
        You are a Trip Planning Assistant. You MUST always return a valid FinalPlan object.
        You must return data that matches this EXACT schema structure:
        {schema_info}

        Your task:
        - Take the research results provided from other specialized agents
        - Synthesize them into a detailed, day-by-day, coherent, and optimized trip plan
        - Make a research plan only for activities and food (always one lodging and one intercity_transport)

        IMPORTANT: You must return a FinalPlan object with either:
        1. A research_plan field populated (if you need more research)
        2. All other fields populated for the final plan (if research is complete)
        3. Use only given candidates

        Never return None or an empty response.

        [INPUT CONTEXT]
        {state}
        {runtime.context}
        """
        plan = await structured_llm.ainvoke(prompt)
        if plan.research_plan:
            return {
                "messages": [
                    AIMessage(content=f"Research plan: {plan}", name="research_plan")
                ],
                "final_plan": plan,
            }
        return {
            "messages": [
                AIMessage(content=f"Final plan: {plan}", name="final_plan")
            ],
            "final_plan": plan,
        }

    return node


def make_combined_human_review_node():
    """Return a node that pauses execution to collect human selections."""

    async def node(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
        interrupts_needed: List[Dict[str, Any]] = []

        if state.lodging and state.lodging.lodging:
            interrupts_needed.append(
                {
                    "type": "lodging",
                    "task": "Choose lodging option",
                    "options": [lodging.model_dump() for lodging in state.lodging.lodging],
                }
            )

        if state.intercity_transport and state.intercity_transport.transport:
            interrupts_needed.append(
                {
                    "type": "intercity_transport",
                    "task": "Choose intercity_transport option",
                    "options": [
                        transport.model_dump()
                        for transport in state.intercity_transport.transport
                    ],
                }
            )

        if not interrupts_needed:
            return {}

        from langgraph.types import interrupt

        result = interrupt(
            {
                "task": "Make your selections for the following options",
                "selections": interrupts_needed,
            }
        )

        response: Dict[str, Any] = {}
        if "lodging" in result:
            selected = CandidateLodging(**result["lodging"])
            response["lodging"] = LodgingAgentOutput(lodging=[selected])
        if "intercity_transport" in result:
            selected = CandidateIntercityTransport(**result["intercity_transport"])
            response["intercity_transport"] = IntercityTransportAgentOutput(
                transport=[selected]
            )
        return response

    return node


def route_from_planner(state: State, runtime: Runtime[Context]) -> Union[str, List[str]]:
    """Decide which follow-up nodes to schedule based on planner output."""

    if not state.final_plan or not state.final_plan.research_plan:
        return END

    plan = state.final_plan.research_plan
    nodes: List[str] = []

    if plan.activities_candidates:
        nodes.append("research_activities")
    if plan.food_candidates:
        nodes.append("research_food")
    if getattr(plan, "recommendations", None): 
        nodes.append("research_recommendations")

    return nodes or END


def build_research_graph(
    *,
    budget_estimate_node,
    research_plan_node,
    lodging_node,
    activities_node,
    food_node,
    intercity_node,
    recommendations_node,
    planner_node,
    human_review_node,
    memory: Optional[InMemorySaver] = None,
) -> Any:
    """Wire all nodes into a compiled LangGraph state machine."""

    graph_builder = StateGraph(state_schema=State, context_schema=Context)

    graph_builder.add_node(budget_estimate_node, name="budget_estimate")
    graph_builder.add_node(research_plan_node, name="research_plan")
    graph_builder.add_node(lodging_node, name="research_lodging")
    graph_builder.add_node(activities_node, name="research_activities")
    graph_builder.add_node(food_node, name="research_food")
    graph_builder.add_node(intercity_node, name="research_intercity_transport")
    graph_builder.add_node(recommendations_node, name="research_recommendations")
    graph_builder.add_node(human_review_node, name="combined_human_review")
    graph_builder.add_node(planner_node, name="planner")

    graph_builder.add_edge(START, "budget_estimate")
    graph_builder.add_edge("budget_estimate", "research_plan")

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

    graph_builder.add_edge("combined_human_review", "planner")
    graph_builder.add_conditional_edges("planner", path=route_from_planner)

    return graph_builder.compile(checkpointer=memory or InMemorySaver())
