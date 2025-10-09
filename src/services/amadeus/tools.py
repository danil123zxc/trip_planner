from amadeus import Client
from langchain_core.tools import Tool, StructuredTool
from typing import Dict, Any
from amadeus.client.errors import ResponseError
from src.services.amadeus.schemas import FlightSearchInput
from src.services.amadeus.client import _format_response_error

def create_flight_search_tool(client: Client) -> Tool:
    """Expose the Amadeus flight search as a LangChain tool."""

    def _run(**kwargs) -> Dict[str, Any]:
        payload = FlightSearchInput(**kwargs)
        search_params = payload.model_dump(mode="json", exclude_none=True)
        try:
            response = client.shopping.flight_offers_search.get(**search_params)
        except ResponseError as exc:
            message = _format_response_error(exc)
            raise RuntimeError(message) from exc
        return response.result

    return StructuredTool.from_function(
        name="search_flights_tool",
        description="Search for flights using the Amadeus flight offers endpoint.",
        func=_run,
        args_schema=FlightSearchInput,
    )