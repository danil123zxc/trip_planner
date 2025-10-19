"""Tests for state reducer functions."""
from __future__ import annotations

import pytest

from src.core.schemas import (
    ActivitiesAgentOutput,
    CandidateActivity,
    CandidateFood,
    CandidateIntercityTransport,
    CandidateLodging,
    FoodAgentOutput,
    IntercityTransportAgentOutput,
    LodgingAgentOutput,
    State
)
from src.core.reducer import reducer
from langchain_core.messages import HumanMessage


def test_state_reducer_merges_lodging():
    """Test that State uses reducer to merge lodging outputs."""
    
    # Create initial state with one hotel
    state1 = State(
        messages=[HumanMessage(content="test")],
        lodging=LodgingAgentOutput(lodging=[
            CandidateLodging(id="1", name="Hotel A")
        ])
    )
    
    # Update with new hotel
    state2 = State(
        messages=[HumanMessage(content="test2")],
        lodging=LodgingAgentOutput(lodging=[
            CandidateLodging(id="2", name="Hotel B")
        ])
    )
    
    # In LangGraph, the reducer would be called automatically
    # But we can test it directly
    merged_lodging = reducer(state1.lodging, state2.lodging)
    
    assert len(merged_lodging.lodging) == 2
    assert merged_lodging.lodging[0].name == "Hotel A"
    assert merged_lodging.lodging[1].name == "Hotel B"

class TestReducer:
    """Test suite for the generic reducer function."""

    def test_merge_both_none_returns_none(self):
        """Test that merging two None values returns None."""
        result = reducer(None, None)
        assert result is None

    def test_merge_existing_none_returns_new(self):
        """Test that when existing is None, new value is returned."""
        new = LodgingAgentOutput(lodging=[
            CandidateLodging(id="1", name="Hotel A")
        ])
        result = reducer(None, new)
        
        assert result is not None
        assert len(result.lodging) == 1
        assert result.lodging[0].name == "Hotel A"

    def test_merge_appends_new_items_to_existing(self):
        """Test that new items are appended to existing items."""
        existing = LodgingAgentOutput(lodging=[
            CandidateLodging(id="1", name="Hotel A"),
            CandidateLodging(id="2", name="Hotel B"),
        ])
        new = LodgingAgentOutput(lodging=[
            CandidateLodging(id="3", name="Hotel C"),
        ])
        
        result = reducer(existing, new)
        
        assert len(result.lodging) == 3
        assert result.lodging[0].name == "Hotel A"
        assert result.lodging[1].name == "Hotel B"
        assert result.lodging[2].name == "Hotel C"

    def test_merge_deduplicates_by_id(self):
        """Test that items with same ID are not duplicated."""
        existing = LodgingAgentOutput(lodging=[
            CandidateLodging(id="1", name="Hotel A"),
            CandidateLodging(id="2", name="Hotel B"),
        ])
        new = LodgingAgentOutput(lodging=[
            CandidateLodging(id="2", name="Hotel B Updated"),  # Same ID
            CandidateLodging(id="3", name="Hotel C"),
        ])
        
        result = reducer(existing, new)
        
        # Should have 3 items, not 4 (duplicate ID "2" filtered out)
        assert len(result.lodging) == 3
        assert result.lodging[0].name == "Hotel A"
        assert result.lodging[1].name == "Hotel B"  # Original kept
        assert result.lodging[2].name == "Hotel C"


    def test_works_with_all_agent_output_types(self):
        """Test that reducer works with all agent output types."""
        # Lodging
        lodging_result = reducer(
            LodgingAgentOutput(lodging=[CandidateLodging(id="1", name="Hotel A")]),
            LodgingAgentOutput(lodging=[CandidateLodging(id="2", name="Hotel B")])
        )
        assert len(lodging_result.lodging) == 2
        
        # Activities
        activities_result = reducer(
            ActivitiesAgentOutput(activities=[CandidateActivity(id="1", name="Museum")]),
            ActivitiesAgentOutput(activities=[CandidateActivity(id="2", name="Park")])
        )
        assert len(activities_result.activities) == 2
        
        # Food
        food_result = reducer(
            FoodAgentOutput(food=[CandidateFood(id="1", name="Restaurant A")]),
            FoodAgentOutput(food=[CandidateFood(id="2", name="Restaurant B")])
        )
        assert len(food_result.food) == 2
        
        # Transport
        transport_result = reducer(
            IntercityTransportAgentOutput(intercity_transport=[
                CandidateIntercityTransport(name="Flight 1", price=100)
            ]),
            IntercityTransportAgentOutput(intercity_transport=[
                CandidateIntercityTransport(name="Flight 2", price=150)
            ])
        )
        assert len(transport_result.intercity_transport) == 2
