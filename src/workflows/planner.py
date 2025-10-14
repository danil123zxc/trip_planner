"""Compatibility layer exposing the planner workflow helpers.

Historically the notebook exported all workflow helpers from ``src.workflows.planner``.
The underlying implementation now lives in ``src.core`` modules. This file re-exports
the public surface so existing imports continue to work unchanged.
"""
from __future__ import annotations

from src.core.agents_builder import build_research_agents as _build_research_agents
from src.core.graph_builder import build_research_graph as _build_research_graph
from src.core.nodes import (
    ResearchAgents as _ResearchAgents,
    make_activities_node,
    make_budget_estimate_node,
    make_combined_human_review_node,
    make_food_node,
    make_intercity_transport_node,
    make_lodging_node,
    make_planner_node,
    make_recommendations_node,
    make_research_plan_node,
    route_from_human_response,
)
from src.core.domain import (
    ActivitiesAgentOutput,
    BudgetEstimate,
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

build_research_agents = _build_research_agents
build_research_graph = _build_research_graph
ResearchAgents = _ResearchAgents

__all__ = [
    "ActivitiesAgentOutput",
    "BudgetEstimate",
    "CandidateActivity",
    "CandidateFood",
    "CandidateIntercityTransport",
    "CandidateLodging",
    "CandidateResearch",
    "Context",
    "FinalPlan",
    "FoodAgentOutput",
    "IntercityTransportAgentOutput",
    "LodgingAgentOutput",
    "RecommendationsOutput",
    "ResearchAgents",
    "ResearchPlan",
    "State",
    "build_research_agents",
    "build_research_graph",
    "make_activities_node",
    "make_budget_estimate_node",
    "make_combined_human_review_node",
    "make_food_node",
    "make_intercity_transport_node",
    "make_lodging_node",
    "make_planner_node",
    "make_recommendations_node",
    "make_research_plan_node",
    "route_from_human_response",
]
