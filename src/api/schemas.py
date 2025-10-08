from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from src.core.domain import Context
from src.core.domain import CandidateLodging, CandidateIntercityTransport, CandidateActivity, CandidateFood
from src.core.domain import RecommendationsOutput, ResearchPlan, BudgetEstimate, FinalPlan

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
        default=None,
        description="Context of the trip being planned.(Specify only if you didn't plan the trip before)"
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