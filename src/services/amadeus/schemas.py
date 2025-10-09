from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_serializer


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
