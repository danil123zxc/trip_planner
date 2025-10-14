"""Backward-compatible re-export of trip planner domain models.

The canonical definitions live in ``src.core.schemas``.  This module exists so
that legacy imports (``from src.core.domain import ...``) continue to work
across the codebase and tests without modification.
"""
from __future__ import annotations

from . import schemas as _schemas

# Re-export all public symbols from schemas
from .schemas import (  # noqa: F401
    ActivitiesAgentOutput,
    BudgetEstimate,
    CandidateActivity,
    CandidateBase,
    CandidateFood,
    CandidateIntercityTransport,
    CandidateLodging,
    CandidateResearch,
    Context,
    FinalPlan,
    FoodAgentOutput,
    IntercityTransportAgentOutput,
    IntracityHop,
    LodgingAgentOutput,
    PlanForDay,
    RecommendationsOutput,
    ResearchAgents,
    ResearchPlan,
    State,
    Transfer,
    Traveller,
)

__all__ = list(_schemas.__all__)
