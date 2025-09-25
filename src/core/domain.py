"""Pydantic data models extracted from the trip planner notebook."""
from __future__ import annotations

from datetime import date
from typing import Annotated, Dict, List, Literal, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from src.core.types import (
    HttpURLStr,
    ISO4217,
    Lat,
    Lon,
    NonNegMoney,
    Rating,
    TimeHHMM,
)


class BudgetEstimate(BaseModel):
    """Budget breakdown covering all major travel cost categories."""
    budget_level: Optional[Literal["$", "$$", "$$$", "$$$$"]] = Field(
        default=None, description="Qualitative budget level"
    )
    currency: ISO4217 = Field(description="ISO currency code, e.g. USD")
    intercity_transport: NonNegMoney = Field(description="Spend for intercity transport")
    local_transport: NonNegMoney = Field(description="Spend for local transport")
    food: NonNegMoney = Field(description="Spend for food & drinks")
    activities: NonNegMoney = Field(description="Spend for entertainment & activities")
    lodging: NonNegMoney = Field(description="Spend for lodging")
    other: NonNegMoney = Field(default=0, description="Miscellaneous budget")
    budget_per_day: NonNegMoney = Field(description="Average daily budget")
    notes: Optional[str] = Field(default=None, description="Assumptions and rationale")

    model_config = ConfigDict(extra="forbid")

    @computed_field(return_type=float)
    @property
    def total(self) -> float:
        """Return the total aggregated budget."""

        return float(
            self.intercity_transport
            + self.local_transport
            + self.food
            + self.activities
            + self.lodging
            + self.other
        )


class CandidateResearch(BaseModel):
    """Instructions describing how many candidates each agent should gather."""
    name: Optional[str] = Field(default=None, description="Name of the research task")
    description: Optional[str] = Field(
        default=None, description="Detailed requirements for the candidates"
    )
    candidates_number: Optional[int] = Field(
        default=None, description="Number of candidates to fetch"
    )


class ResearchPlan(BaseModel):
    """Top-level container mapping each research domain to its constraints."""
    lodging_candidates: Optional[CandidateResearch] = None
    activities_candidates: Optional[CandidateResearch] = None
    food_candidates: Optional[CandidateResearch] = None
    intercity_transport_candidates: Optional[CandidateResearch] = None
    local_transport_candidates: Optional[CandidateResearch] = None
    recommendations: Optional[CandidateResearch] = None

    model_config = ConfigDict(extra="forbid")


class CandidateBase(BaseModel):
    """Common attributes shared by all researched trip candidates."""
    id: Optional[str] = None
    name: str
    address: Optional[str] = None
    price_level: Optional[Literal["$", "$$", "$$$", "$$$$"]] = None
    rating: Optional[Rating] = None
    reviews: Optional[List[str]] = None
    photos: Optional[List[HttpURLStr]] = None
    url: Optional[HttpURLStr] = None
    lat: Optional[Lat] = None
    lon: Optional[Lon] = None
    evidence_score: Annotated[float, Field(ge=0, le=1)] = 0.0
    source_id: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CandidateLodging(CandidateBase):
    """Structured lodging option produced by the lodging research agent."""
    area: Optional[str] = None
    price_night: Optional[NonNegMoney] = None
    cancel_policy: Optional[str] = None


class LodgingAgentOutput(BaseModel):
    """Envelope for lodging candidates returned from the agent layer."""
    lodging: List[CandidateLodging]

    model_config = ConfigDict(extra="forbid")


class CandidateActivity(CandidateBase):
    """Activity suggestion that can be scheduled in the final itinerary."""
    open_time: Optional[TimeHHMM] = None
    close_time: Optional[TimeHHMM] = None
    duration_min: Optional[int] = Field(default=None, ge=0, le=12 * 60)
    price: Optional[NonNegMoney] = None
    tags: List[str] = Field(default_factory=list)


class ActivitiesAgentOutput(BaseModel):
    """Container for the activity research agent response."""
    activities: List[CandidateActivity]

    model_config = ConfigDict(extra="forbid")


class CandidateFood(CandidateBase):
    """Food or dining option surfaced by the culinary research agent."""
    open_time: Optional[TimeHHMM] = None
    close_time: Optional[TimeHHMM] = None
    tags: List[str] = Field(default_factory=list)


class FoodAgentOutput(BaseModel):
    """Wrapper around food candidates for downstream consumption."""
    food: List[CandidateFood]

    model_config = ConfigDict(extra="forbid")


class Transfer(BaseModel):
    """Single leg inside an intercity journey (flight, rail, bus, etc.)."""
    name: str
    place: str
    departure_time: Optional[TimeHHMM] = None
    arrival_time: Optional[TimeHHMM] = None
    duration_min: Optional[int] = Field(default=None, ge=0, le=7 * 24 * 60)

    model_config = ConfigDict(extra="forbid")


class CandidateIntercityTransport(BaseModel):
    """Complete intercity option including legs, fare info, and notes."""
    name: str
    fare_class: Optional[str] = None
    refundable: Optional[bool] = None
    url: Optional[HttpURLStr] = None
    price: Optional[NonNegMoney] = None
    transfer: List[Transfer] = Field(default_factory=list)
    total_duration_min: Optional[int] = Field(default=None, ge=0, le=7 * 24 * 60)
    note: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class IntercityTransportAgentOutput(BaseModel):
    """Agent payload bundling the researched intercity transport options."""
    transport: List[CandidateIntercityTransport]

    model_config = ConfigDict(extra="forbid")


class IntracityHop(BaseModel):
    """Short, within-destination transfer that links daily activities."""
    mode: Literal["walk", "bus", "subway", "taxi", "bike", "rideshare", "tram", "ferry"]
    from_place: Optional[str] = None
    to_place: Optional[str] = None
    duration_min: Optional[int] = Field(default=None, ge=0, le=24 * 60)

    model_config = ConfigDict(extra="forbid")


class RecommendationsOutput(BaseModel):
    """Holistic travel advice spanning safety, cultural, and logistical tips."""
    safety_level: Literal["very_safe", "safe", "moderate", "risky", "dangerous"]
    safety_notes: Optional[List[str]] = Field(default_factory=list)
    travel_advisories: Optional[List[str]] = Field(default_factory=list)
    visa_requirements: Optional[Dict[str, str]] = Field(default_factory=dict)
    cultural_considerations: Optional[List[str]] = Field(default_factory=list)
    dress_code_recommendations: Optional[List[str]] = Field(default_factory=list)
    local_customs: Optional[List[str]] = Field(default_factory=list)
    language_barriers: Optional[List[str]] = Field(default_factory=list)
    child_friendly_rating: int = Field(ge=1, le=5)
    infant_considerations: Optional[List[str]] = Field(default_factory=list)
    elderly_accessibility: Optional[List[str]] = Field(default_factory=list)
    weather_conditions: Optional[str] = None
    seasonal_considerations: Optional[List[str]] = Field(default_factory=list)
    best_time_to_visit: Optional[str] = None
    currency_info: Optional[str] = None
    payment_methods: Optional[List[str]] = Field(default_factory=list)
    religious_restrictions: Optional[List[str]] = Field(default_factory=list)
    dietary_restrictions_support: Optional[Dict[str, bool]] = Field(default_factory=dict)


class PlanForDay(BaseModel):
    """Represents a single day in the itinerary with budget and activities."""
    day_number: int = Field(ge=1)
    day_date: date
    activities: List[CandidateActivity] = Field(default_factory=list)
    food: List[CandidateFood] = Field(default_factory=list)
    intracity_moves: List[IntracityHop] = Field(default_factory=list)
    day_budget: NonNegMoney
    start_time: Optional[TimeHHMM] = None
    end_time: Optional[TimeHHMM] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class FinalPlan(BaseModel):
    """Completed itinerary or a follow-up research request from the planner."""
    days: Optional[List[PlanForDay]] = None
    total_budget: Optional[NonNegMoney] = None
    lodging: Optional[CandidateLodging] = None
    intercity_transport: Optional[CandidateIntercityTransport] = None
    currency: Optional[ISO4217] = None
    research_plan: Optional[ResearchPlan] = None

    model_config = ConfigDict(extra="forbid")


class OutputSchema(BaseModel):
    """Legacy schema kept for backwards compatibility with earlier outputs."""
    days: List[PlanForDay]
    total_budget: NonNegMoney
    currency: Optional[ISO4217] = Field(default="USD")

    model_config = ConfigDict(extra="forbid")


class State(BaseModel):
    """Graph state that flows between LangGraph nodes during execution."""
    messages: Annotated[List[AnyMessage], add_messages]
    destination_coordinates: Optional[str] = None
    estimated_budget: Optional[BudgetEstimate] = None
    research_plan: Optional[ResearchPlan] = None
    lodging: Optional[LodgingAgentOutput] = None
    activities: Optional[ActivitiesAgentOutput] = None
    food: Optional[FoodAgentOutput] = None
    intercity_transport: Optional[IntercityTransportAgentOutput] = None
    recommendations: Optional[RecommendationsOutput] = None
    final_plan: Optional[FinalPlan] = None

    model_config = ConfigDict(extra="forbid")


class Traveller(BaseModel):
    """Minimal traveller profile used to evaluate budgets and preferences."""
    name: str
    date_of_birth: date
    spoken_languages: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    nationality: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @computed_field(return_type=str)
    @property
    def age_group(self) -> Literal["infant", "child", "adult"]:
        today = date.today()
        age = today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        if age < 2:
            return "infant"
        if age < 18:
            return "child"
        return "adult"


class Context(BaseModel):
    """Immutable configuration describing the trip being planned."""
    travellers: List[Traveller] = Field(default_factory=list)
    budget: NonNegMoney = Field(default=1000)
    currency: ISO4217 = Field(default="USD")
    destination: str
    destination_country: str
    date_from: date
    date_to: date
    group_type: Literal["family", "couple", "alone", "friends", "business"]
    trip_purpose: Optional[str] = None
    current_location: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_dates(self) -> "Context":
        if self.date_from > self.date_to:
            raise ValueError("date_from must be before or equal to date_to")
        return self

    @computed_field(return_type=int)
    @property
    def days_number(self) -> int:
        return (self.date_to - self.date_from).days + 1

    @computed_field(return_type=int)
    @property
    def adults_num(self) -> int:
        return sum(1 for traveller in self.travellers if traveller.age_group == "adult")

    @computed_field(return_type=int)
    @property
    def children_num(self) -> int:
        return sum(1 for traveller in self.travellers if traveller.age_group == "child")

    @computed_field(return_type=int)
    @property
    def infant_num(self) -> int:
        return sum(1 for traveller in self.travellers if traveller.age_group == "infant")
