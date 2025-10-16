from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_serializer
from src.core.types import ISO4217

class FlightSearchInput(BaseModel):
    """Input schema mirroring the Amadeus flight offers endpoint."""

    originLocationCode: str = Field(..., description="Origin airport/city IATA code")
    destinationLocationCode: str = Field(..., description="Destination airport/city IATA code")
    departureDate: date = Field(..., description="Outbound date (YYYY-MM-DD)")
    returnDate: Optional[date] = Field(None, description="Return date for round trip")
    adults: str = Field("1", description="Number of adults")
    children: Optional[str] = Field(None, description="Number of children")
    infants: Optional[str] = Field(None, description="Number of infants")
    travelClass: Optional[Literal["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]] = Field(
        None,
        description="Cabin class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST",
    )
    maxPrice: Optional[str] = Field(None, description="Maximum price in the selected currency")
    currencyCode: Optional[ISO4217] = Field(None, description="Currency code")
    max: Optional[str] = Field(None, description="Number of flight offers to return")

    @field_serializer("departureDate", "returnDate", when_used="json")
    def _serialize_dates(self, value: Optional[date], _info) -> Optional[str]:
        if value is None:
            return None
        return value.strftime("%Y-%m-%d")
