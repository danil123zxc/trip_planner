from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Optional, Any
from src.core.schemas import State, Context, ResearchAgents
from src.core.nodes import make_budget_estimate_node, make_research_plan_node, make_lodging_node, make_activities_node, make_food_node, make_intercity_transport_node, make_recommendations_node, make_combined_human_review_node, make_planner_node
from src.core.nodes import route_from_human_response

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
