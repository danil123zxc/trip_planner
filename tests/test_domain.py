"""Tests for domain models and data validation."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from src.core.domain import (
    BudgetEstimate,
    CandidateActivity,
    CandidateFood,
    CandidateIntercityTransport,
    CandidateLodging,
    CandidateResearch,
    Context,
    FinalPlan,
    ResearchPlan,
    State,
)


def test_budget_estimate_creation():
    """Test creating a valid budget estimate."""
    budget = BudgetEstimate(
        budget_level="$$",
        currency="USD",
        intercity_transport=400,
        local_transport=200,
        food=600,
        activities=500,
        lodging=700,
        other=100,
        budget_per_day=350,
    )
    assert budget.total == 2500.0
    assert budget.currency == "USD"
    assert budget.budget_level == "$$"


def test_budget_estimate_missing_required_fields():
    """Test that missing required fields raise validation errors."""
    with pytest.raises(ValidationError):
        BudgetEstimate(
            budget_level="$$",
            currency="USD",
            # Missing required fields
        )


def test_context_creation():
    """Test creating a valid context."""
    context = Context(
        destination="Tokyo",
        destination_country="Japan",
        date_from=date(2025, 1, 10),
        date_to=date(2025, 1, 17),
        budget=2500,
        currency="USD",
        group_type="couple",
    )
    assert context.destination == "Tokyo"
    assert context.days_number == 8  # Should be calculated automatically (inclusive)


def test_context_invalid_dates():
    """Test that invalid date ranges are rejected."""
    with pytest.raises(ValidationError):
        Context(
            destination="Tokyo",
            destination_country="Japan",
            date_from=date(2025, 1, 17),  # Start after end
            date_to=date(2025, 1, 10),
            budget=2500,
            currency="USD",
            group_type="couple",
        )


def test_research_plan_creation():
    """Test creating a valid research plan."""
    plan = ResearchPlan(
        lodging_candidates=CandidateResearch(candidates_number=3),
        activities_candidates=CandidateResearch(candidates_number=5),
        food_candidates=CandidateResearch(candidates_number=4),
        intercity_transport_candidates=CandidateResearch(candidates_number=2),
        recommendations=CandidateResearch(candidates_number=1),
    )
    assert plan.lodging_candidates.candidates_number == 3
    assert plan.activities_candidates.candidates_number == 5


def test_candidate_models():
    """Test creating candidate models."""
    lodging = CandidateLodging(
        name="Hotel Aurora",
        address="Tokyo",
        price_night=150,
        rating=4.5,
    )
    assert lodging.name == "Hotel Aurora"
    assert lodging.price_night == 150

    activity = CandidateActivity(
        name="Sushi Workshop",
        address="Tokyo",
        price=80,
        duration_min=120,
    )
    assert activity.name == "Sushi Workshop"
    assert activity.duration_min == 120

    food = CandidateFood(
        name="Ramen House",
        address="Tokyo",
    )
    assert food.name == "Ramen House"

    transport = CandidateIntercityTransport(
        name="Bullet Train",
        price=120,
        total_duration_min=150,
    )
    assert transport.name == "Bullet Train"
    assert transport.total_duration_min == 150


def test_final_plan_creation():
    """Test creating a final plan."""
    lodging = CandidateLodging(name="Hotel Aurora", price_night=150)
    transport = CandidateIntercityTransport(name="Bullet Train", price=120)
    
    plan = FinalPlan(
        total_budget=2500,
        currency="USD",
        lodging=lodging,
        intercity_transport=transport,
    )
    assert plan.total_budget == 2500
    assert plan.currency == "USD"
    assert plan.lodging.name == "Hotel Aurora"


def test_state_creation():
    """Test creating a state object."""
    state = State(messages=[])
    assert state.messages == []
    assert state.estimated_budget is None
    assert state.research_plan is None
