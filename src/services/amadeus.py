"""Amadeus flight search integration."""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from amadeus import Client
from langchain_core.tools import Tool
from pydantic import BaseModel, Field, field_serializer

from src.core.config import ApiSettings


class FlightSearchInput(BaseModel):
    """Input schema mirroring the Amadeus flight offers endpoint."""

    originLocationCode: str = Field(..., description="Origin airport/city code")
    destinationLocationCode: str = Field(..., description="Destination airport/city code")
    departureDate: date = Field(..., description="Outbound date (YYYY-MM-DD)")
    returnDate: Optional[date] = Field(None, description="Return date for round trip")
    adults: Optional[int] = Field(1, ge=1, le=9, description="Number of adults")
    children: Optional[int] = Field(0, ge=0, le=9, description="Number of children")
    infants: Optional[int] = Field(0, ge=0, le=9, description="Number of infants")
    travelClass: Optional[str] = Field(
        "ECONOMY",
        description="Cabin class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST",
    )
    maxPrice: Optional[int] = Field(None, description="Maximum price in the selected currency")
    currencyCode: Optional[str] = Field("USD", description="Currency code")
    max: Optional[int] = Field(10, ge=1, le=50, description="Number of flight offers to return")

    @field_serializer("departureDate", "returnDate", when_used="json")
    def _serialize_dates(self, value: Optional[date], _info) -> Optional[str]:
        if value is None:
            return None
        return value.strftime("%Y-%m-%d")


def create_amadeus_client(settings: ApiSettings, *, hostname: str = "test") -> Client:
    """Instantiate the Amadeus SDK client using project configuration."""

    client_id = settings.ensure("amadeus_api_key")
    client_secret = settings.ensure("amadeus_api_secret")
    return Client(client_id=client_id, client_secret=client_secret, hostname=hostname)


def create_flight_search_tool(client: Client) -> Tool:
    """Expose the Amadeus flight search as a LangChain tool."""

    def _run(params: Dict[str, Any]) -> Dict[str, Any]:
        payload = FlightSearchInput(**params)
        search_params = payload.model_dump(mode="json", exclude_none=True)
        response = client.shopping.flight_offers_search.get(**search_params)
        return response.result

    return Tool(
        name="search_flights",
        description="Search for flights using the Amadeus flight offers endpoint.",
        func=_run,
    )
