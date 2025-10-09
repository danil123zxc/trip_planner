"""External service integrations for trip planning.

This package provides clients and LangChain tool factories for various external
services used in the trip planning workflow:

- Amadeus: Flight search and booking
- TripAdvisor: Location search, details, photos, and reviews
- Reddit: Community insights and travel recommendations
- Tavily: Internet search for general web research
- Geocoding: Address and coordinate resolution

Each service module exports:
    - create_*_client: Factory to create the API client
    - create_*_tool(s): Factory to create LangChain tools from the client
    - Input schemas: Pydantic models for tool parameters

Example Usage:
    >>> from src.services.amadeus import create_amadeus_client, create_flight_search_tool
    >>> from src.core.config import ApiSettings
    >>> 
    >>> settings = ApiSettings.from_env()
    >>> client = create_amadeus_client(settings)
    >>> tool = create_flight_search_tool(client)
"""

# Amadeus flight search
from src.services.amadeus import (
    create_amadeus_client,
    create_flight_search_tool,
    FlightSearchInput,
)

# TripAdvisor location research
from src.services.trip_advisor import (
    TripAdvisor,
    create_trip_advisor_client,
    create_trip_advisor_tools,
    ComprehensiveLocationInput,
    SearchLocation,
    LocationDetails,
    LocationPhotos,
    LocationReviews,
    NearbySearch,
)

# Reddit search
from src.services.reddit import (
    create_reddit_tool,
    parse_reddit_results,
    RedditSearchInput,
)

# Internet search via Tavily
from src.services.tavily_search import (
    create_internet_tool,
    process_pages,
    InternetSearchInput,
)

# Geocoding
from src.services.geocoding import get_coordinates_nominatim

__all__ = [
    # Amadeus
    "create_amadeus_client",
    "create_flight_search_tool",
    "FlightSearchInput",
    # TripAdvisor
    "TripAdvisor",
    "create_trip_advisor_client",
    "create_trip_advisor_tools",
    "ComprehensiveLocationInput",
    "SearchLocation",
    "LocationDetails",
    "LocationPhotos",
    "LocationReviews",
    "NearbySearch",
    # Reddit
    "create_reddit_tool",
    "parse_reddit_results",
    "RedditSearchInput",
    # Tavily/Internet
    "create_internet_tool",
    "process_pages",
    "InternetSearchInput",
    # Geocoding
    "get_coordinates_nominatim",
]

