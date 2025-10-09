from src.services.trip_advisor.client import TripAdvisor
from langchain_core.tools import Tool, StructuredTool
from typing import Any
from src.services.trip_advisor.schemas import ComprehensiveLocationInput


def create_trip_advisor_tools(client: TripAdvisor) -> Tool:
    """Generate the LangChain tools backed by the TripAdvisor client.
    
    Creates a collection of LangChain tools that wrap the TripAdvisor API client
    methods, making them available for use in LangChain agents and workflows.
    
    Args:
        client: An initialized TripAdvisor client instance
        
    Returns:
        Tool: LangChain Tool object
        
    Tools Created:
        - comprehensive_search_tool: Perform complete search with details/photos/reviews
    """

    async def comprehensive(**kwargs) -> Any:
        """Perform comprehensive location search with full details.
        
        This is the most powerful tool that combines search with detailed information
        gathering. It searches for locations and then fetches complete details,
        photos, and reviews for each result in a single operation.
        
        Args:
            search_input: ComprehensiveLocationInput object containing search parameters:
                - searchQuery (str): The search query (required)
                - latLong (str, optional): Latitude,longitude for location-based search
                - category (str, optional): Filter by type ("attractions", "restaurants", "geos", "hotels")
                - phone (str, optional): Filter by phone number
                - address (str, optional): Filter by address
                - radius (int, optional): Search radius (requires latLong)
                - radiusUnit (str, optional): Unit for radius ("km", "mi", "m")
                - language (str, optional): Response language (default: "en")
                - limit_locations (int, optional): Max locations to process (default: 5)
                - photos_limit (int, optional): Max photos per location (default: 10)
                - reviews_limit (int, optional): Max reviews per location (default: 10)
                - currency (str, optional): Currency for pricing (default: "USD")
                - offset_photos (int, optional): Photo offset for pagination
                - offset_reviews (int, optional): Review offset for pagination

        Returns:
            List[ComprehensiveLocationResult]: Complete location data including:
                - Basic location information
                - Detailed descriptions and contact info
                - Photo collections with metadata
                - Review collections with ratings
                - Error information for failed requests

        Example:
            search_input = ComprehensiveLocationInput(
                searchQuery="cultural attractions in Tokyo",
                category="attractions",
                limit_locations=3,
                photos_limit=15,
                reviews_limit=20,
                language="en",
                currency="USD"
            )
            comprehensive(**search_input)

        Note:
            This tool performs multiple API calls per location and may take longer
            to complete than individual search tools. Use limit_locations to control
            processing time and API usage.
        """

        return await client.comprehensive_search(ComprehensiveLocationInput(**kwargs))

    return StructuredTool.from_function(
            coroutine=comprehensive,
            name="comprehensive_search_tool",
            description="Perform complete location research: search + details + photos + reviews in one operation. Most comprehensive but slower. Input: ComprehensiveLocationInput object with searchQuery (required) and optional parameters: latLong, category (attractions/restaurants/geos/hotels), phone, address, radius, radiusUnit (km/mi/m), language (default: en), limit_locations (default: 5), photos_limit (default: 10), reviews_limit (default: 10), currency (default: USD), offset_photos, offset_reviews.",
            args_schema=ComprehensiveLocationInput,
        )
    