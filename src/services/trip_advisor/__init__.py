"""TripAdvisor Content API integration.

This module provides client and tool factories for integrating TripAdvisor's
comprehensive location search, details, photos, and reviews into LangChain-based
travel planning workflows.

Public API:
    - TripAdvisor: Async HTTP client for TripAdvisor Content API
    - create_trip_advisor_client: Factory function to create TripAdvisor client
    - create_trip_advisor_tools: Factory function to create LangChain tools
    - ComprehensiveLocationInput: Pydantic schema for comprehensive search parameters
"""
from src.services.trip_advisor.client import TripAdvisor, create_trip_advisor_client
from src.services.trip_advisor.tools import create_trip_advisor_tools
from src.services.trip_advisor.schemas import (
    ComprehensiveLocationInput,
    ComprehensiveLocationResult,
    SearchLocation,
    LocationDetails,
    LocationPhotos,
    LocationReviews,
    NearbySearch,
)

__all__ = [
    "TripAdvisor",
    "create_trip_advisor_client",
    "create_trip_advisor_tools",
    "ComprehensiveLocationInput",
    "ComprehensiveLocationResult",
    "SearchLocation",
    "LocationDetails",
    "LocationPhotos",
    "LocationReviews",
    "NearbySearch",
]

