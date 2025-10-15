from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from src.core.schemas import Context
from src.core.schemas import CandidateLodging, CandidateIntercityTransport, CandidateActivity, CandidateFood
from src.core.schemas import RecommendationsOutput, ResearchPlan, BudgetEstimate, FinalPlan

class PlanRequest(Context):
    """Request payload used to start a new planning run."""
    pass

class ResumeSelections(BaseModel):
    """Indices of options chosen during human-in-the-loop review."""

    lodging: CandidateLodging = Field(
        default_factory=CandidateLodging,
        description="Selected lodging option.",
    )
    intercity_transport: CandidateIntercityTransport = Field(
        default_factory=CandidateIntercityTransport,
        description="Selected intercity transport option.",
    )
    activities: List[CandidateActivity] = Field(
        default_factory=list,
        description="Selected activity options.",
    )
    food: List[CandidateFood] = Field(
        default_factory=list,
        description="Selected food options.",
    )

class FinalPlanRequest(BaseModel):
    """Request payload used to return the final plan for the trip planning workflow."""
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="LangGraph configuration object returned by the interrupt response.",
    )
    selections: ResumeSelections = Field(
        default_factory=ResumeSelections,
        description="Indices indicating which options the user selected.",
    )


class ExtraResearchRequest(BaseModel):
    """Request payload used to perform extra research for the trip planning workflow."""

    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="LangGraph configuration object returned by the interrupt response.",
    )
    research_plan: ResearchPlan = Field(    
        default_factory=ResearchPlan,
        description="Overrides for the next research plan. Keys align with CandidateResearch fields.",
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
    lodging: Optional[List[CandidateLodging] | CandidateLodging] = Field(
        default=None, description="Candidate lodging options surfaced by the agent"
    )
    activities: Optional[List[CandidateActivity]] = Field(
        default=None, description="Candidate activities surfaced by the agent"
    )
    food: Optional[List[CandidateFood]] = Field(
        default=None, description="Candidate food options surfaced by the agent"
    )
    intercity_transport: Optional[List[CandidateIntercityTransport] | CandidateIntercityTransport] = Field(
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
    messages: Optional[List[str]] = Field(
        default=None,
        description="Workflow execution log rendered as plain strings"
    )