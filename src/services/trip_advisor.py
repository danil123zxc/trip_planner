"""Async TripAdvisor client and related Pydantic models."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Literal, Optional

import httpx
from langchain_core.tools import Tool
from pydantic import BaseModel, ConfigDict, Field

from src.core.config import ApiSettings
from src.core.types import HttpURLStr, ISO4217, Lat, Lon, Rating

LanguageCode = Literal[
    "ar",
    "zh",
    "zh_TW",
    "da",
    "nl",
    "en_AU",
    "en_CA",
    "en_HK",
    "en_IN",
    "en_IE",
    "en_MY",
    "en_NZ",
    "en_PH",
    "en_SG",
    "en_ZA",
    "en_UK",
    "en",
    "fr",
    "fr_BE",
    "fr_CA",
    "fr_CH",
    "de_AT",
    "de",
    "el",
    "iw",
    "in",
    "it",
    "it_CH",
    "ja",
    "ko",
    "no",
    "pt_PT",
    "pt",
    "ru",
    "es_AR",
    "es_CO",
    "es_MX",
    "es_PE",
    "es",
    "es_VE",
    "es_CL",
    "sv",
    "th",
    "tr",
    "vi",
]


class Address(BaseModel):
    """Normalized postal address returned by TripAdvisor endpoints."""
    street1: Optional[str] = Field(default=None, description="Street address")
    street2: Optional[str] = Field(default=None, description="Street address")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State")
    country: Optional[str] = Field(default=None, description="Country")
    postalcode: Optional[str] = Field(default=None, description="Postal code")
    address_string: Optional[str] = Field(default=None, description="Full address")

    model_config = ConfigDict(extra="forbid")


class NearbySearch(BaseModel):
    """Input payload accepted by the TripAdvisor nearby search endpoint."""
    latLong: str = Field(
        description="Latitude/Longitude pair (e.g., '42.3455,-71.10767')"
    )
    category: Optional[Literal["attractions", "restaurants", "geos", "hotels"]] = Field(
        default=None, description="Filter by property type"
    )
    phone: Optional[str] = Field(default=None, description="Phone number filter")
    address: Optional[str] = Field(default=None, description="Address filter")
    radius: Optional[int] = Field(default=None, ge=0, description="Radius length")
    radiusUnit: Optional[Literal["km", "mi", "m"]] = Field(
        default=None, description="Unit for the radius"
    )
    language: Optional[LanguageCode] = Field(
        default="en", description="Response language"
    )

    model_config = ConfigDict(extra="forbid")


class NearbySearchData(BaseModel):
    """Single result row from a nearby search response."""
    location_id: str
    name: str
    distance: str
    bearing: str
    address_obj: Address

    model_config = ConfigDict(extra="forbid")


class NearbySearchOutput(BaseModel):
    """Wrapper object for nearby search results."""
    data: List[NearbySearchData]


class SearchLocation(BaseModel):
    """Request schema for the TripAdvisor location search endpoint."""
    searchQuery: str
    latLong: Optional[str] = None
    category: Optional[Literal["attractions", "restaurants", "geos", "hotels"]] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    radius: Optional[int] = Field(default=None, ge=0)
    radiusUnit: Optional[Literal["km", "mi", "m"]] = None
    language: Optional[LanguageCode] = Field(default="en")


class LocationData(BaseModel):
    """Slimmed-down description of a location returned from search."""
    location_id: str
    name: str
    address_obj: Address


class LocationOutput(BaseModel):
    """Response model containing multiple `LocationData` entries."""
    data: List[LocationData]

    model_config = ConfigDict(extra="forbid")


class LocationDetails(BaseModel):
    """Request schema for fetching the detailed location profile."""
    locationId: str
    language: Optional[LanguageCode] = Field(default="en")
    currency: Optional[ISO4217] = Field(default="USD")

    model_config = ConfigDict(extra="forbid")


class DetailsOutput(BaseModel):
    """Detailed location metadata enriched with TripAdvisor attributes."""
    location_id: str
    name: str
    description: Optional[str] = None
    web_url: Optional[HttpURLStr] = None
    address_obj: Optional[Address] = None
    latitude: Optional[Lat] = None
    longitude: Optional[Lon] = None
    website: Optional[HttpURLStr] = None
    rating: Optional[Rating] = None
    price_level: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class LocationPhotos(BaseModel):
    """Request schema for retrieving TripAdvisor photo galleries."""
    locationId: str
    language: Optional[LanguageCode] = Field(default="en")
    limit: Optional[int] = None
    offset: Optional[int] = None
    source: Optional[str] = Field(
        default=None,
        description="Comma separated photo source filter (Expert, Management, Traveler)",
    )

    model_config = ConfigDict(extra="forbid")


class Image(BaseModel):
    """Photo metadata that captures dimensions and the CDN URL."""
    height: Optional[int] = None
    width: Optional[int] = None
    url: Optional[HttpURLStr] = None


class PhotosData(BaseModel):
    """Structured record describing a single TripAdvisor photo."""
    id: str
    caption: Optional[str] = None
    published_date: Optional[str] = None
    image: Optional[Image] = None

    model_config = ConfigDict(extra="forbid")


class PhotosOutput(BaseModel):
    """Response container bundling multiple photo entries."""
    data: List[PhotosData]

    model_config = ConfigDict(extra="forbid")


class LocationReviews(BaseModel):
    """Request schema for paginating TripAdvisor review content."""
    locationId: str
    language: Optional[LanguageCode] = Field(default="en")
    limit: Optional[int] = None
    offset: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class ReviewData(BaseModel):
    """Normalized TripAdvisor review fields used downstream."""
    id: str
    lang: LanguageCode
    location_id: str
    published_date: str
    rating: Optional[Rating]
    url: Optional[HttpURLStr]
    text: Optional[str]
    title: Optional[str] = None
    trip_type: Optional[str] = None
    travel_date: Optional[str] = None


class ReviewOutput(BaseModel):
    """Response container with zero or more location reviews."""
    data: List[ReviewData]

    model_config = ConfigDict(extra="forbid")


class ComprehensiveLocationInput(BaseModel):
    """Composite request used by the helper that fans out for details."""
    searchQuery: str
    latLong: Optional[str] = None
    category: Optional[Literal["attractions", "restaurants", "geos", "hotels"]] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    radius: Optional[int] = Field(default=None, ge=0)
    radiusUnit: Optional[Literal["km", "mi", "m"]] = None
    language: Optional[LanguageCode] = Field(default="en")
    limit_locations: Optional[int] = Field(default=5)
    photos_limit: Optional[int] = Field(default=10)
    reviews_limit: Optional[int] = Field(default=10)
    currency: Optional[ISO4217] = Field(default="USD")
    offset_photos: Optional[int] = None
    offset_reviews: Optional[int] = None


class ComprehensiveLocationResult(BaseModel):
    """Aggregated TripAdvisor data for a single location."""
    location_id: str
    name: str
    address: Optional[Address] = None
    details: Optional[DetailsOutput] = None
    photos: Optional[PhotosOutput] = None
    reviews: Optional[ReviewOutput] = None
    error: Optional[str] = None


class TripAdvisor:
    """Thin async wrapper around the TripAdvisor Content API v1."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.content.tripadvisor.com/api/v1",
        timeout_s: float = 15.0,
    ) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"accept": "application/json"},
            timeout=httpx.Timeout(timeout_s, connect=10.0),
        )
        self.api_url = f"{base_url.rstrip('/')}/location"

    async def aclose(self) -> None:
        """Close the underlying HTTPX client."""

        await self._client.aclose()

    async def __aenter__(self) -> "TripAdvisor":
        """Support async context-manager usage."""

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """Ensure the HTTP client is closed when leaving a context."""

        await self._client.aclose()

    async def _aget(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an authenticated GET request and return the parsed JSON."""

        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def search_location(self, input: SearchLocation) -> LocationOutput:
        """Search for TripAdvisor locations that match the provided query."""

        params = {"key": self.api_key, **input.model_dump(exclude_none=True)}
        data = await self._aget(f"{self.api_url}/search", params)
        return LocationOutput(
            data=[
                LocationData(
                    location_id=item["location_id"],
                    name=item["name"],
                    address_obj=Address(**item["address_obj"]),
                )
                for item in data.get("data", [])
            ]
        )

    async def location_details(self, input: LocationDetails) -> DetailsOutput:
        """Fetch rich TripAdvisor details for a given location ID."""

        params = {"key": self.api_key, **input.model_dump(exclude={"locationId"}, exclude_none=True)}
        data = await self._aget(f"{self.api_url}/{input.locationId}/details", params)
        return DetailsOutput(
            location_id=data.get("location_id"),
            name=data.get("name"),
            description=data.get("description"),
            web_url=data.get("web_url"),
            address_obj=data.get("address_obj"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            website=data.get("website"),
            rating=data.get("rating"),
            price_level=data.get("price_level"),
        )

    async def location_photos(self, input: LocationPhotos) -> PhotosOutput:
        """Return TripAdvisor-hosted photos for the requested location."""

        params = {"key": self.api_key, **input.model_dump(exclude={"locationId"}, exclude_none=True)}
        data = await self._aget(f"{self.api_url}/{input.locationId}/photos", params)
        photos: List[PhotosData] = []
        for item in data.get("data", []):
            original = (item.get("images") or {}).get("original") or {}
            # Debug: Print the actual item structure
            print(f"DEBUG - Photo item: {item}")
            # Use the location ID as the photo ID if no specific photo ID exists
            photo_id = input.locationId
            photos.append(
                PhotosData(
                    id=str(photo_id),
                    caption=item.get("caption"),
                    published_date=item.get("published_date"),
                    image=Image(
                        height=original.get("height"),
                        width=original.get("width"),
                        url=original.get("url"),
                    ),
                )
            )
        return PhotosOutput(data=photos)

    async def location_reviews(self, input: LocationReviews) -> ReviewOutput:
        """Retrieve paginated TripAdvisor reviews for the location."""

        params = {"key": self.api_key, **input.model_dump(exclude={"locationId"}, exclude_none=True)}
        data = await self._aget(f"{self.api_url}/{input.locationId}/reviews", params)
        reviews: List[ReviewData] = []
        for item in data.get("data", []):
            # Use the location ID from the input and create review ID based on location
            review_id = input.locationId
            reviews.append(
                ReviewData(
                    id=str(review_id),
                    lang=item.get("lang"),
                    location_id=str(input.locationId),  # Use the location ID from the search
                    published_date=item.get("published_date"),
                    rating=item.get("rating"),
                    url=item.get("url"),
                    text=item.get("text"),
                    title=item.get("title"),
                    trip_type=item.get("trip_type"),
                    travel_date=item.get("travel_date"),
                )
            )
        return ReviewOutput(data=reviews)

    async def nearby_search(self, input: NearbySearch) -> NearbySearchOutput:
        """Find nearby places relative to a latitude/longitude pair."""

        params = {"key": self.api_key, **input.model_dump(exclude_none=True)}
        data = await self._aget(f"{self.api_url}/nearby_search", params)
        results: List[NearbySearchData] = []
        for item in data.get("data", []):
            results.append(
                NearbySearchData(
                    location_id=item.get("location_id"),
                    name=item.get("name"),
                    distance=item.get("distance"),
                    bearing=item.get("bearing"),
                    address_obj=Address(**item["address_obj"]),
                )
            )
        return NearbySearchOutput(data=results)

    async def comprehensive_search(
        self, input: ComprehensiveLocationInput
    ) -> List[ComprehensiveLocationResult]:
        """Perform search + details/photos/reviews fan-out for each location."""

        search_input = SearchLocation(
            searchQuery=input.searchQuery,
            latLong=input.latLong,
            category=input.category,
            language=input.language,
            phone=input.phone,
            address=input.address,
            radius=input.radius,
            radiusUnit=input.radiusUnit,
        )

        search_results = await self.search_location(search_input)
        if not search_results.data:
            return []

        locations = search_results.data[: input.limit_locations or 5]

        async def fetch_all(location: LocationData) -> ComprehensiveLocationResult:
            """Fetch details, photos, and reviews for a single location."""

            result = ComprehensiveLocationResult(
                location_id=location.location_id,
                name=location.name,
                address=location.address_obj,
            )

            details_task = self.location_details(
                LocationDetails(
                    locationId=location.location_id,
                    language=input.language,
                    currency=input.currency,
                )
            )
            photos_task = self.location_photos(
                LocationPhotos(
                    locationId=location.location_id,
                    language=input.language,
                    limit=input.photos_limit,
                    offset=input.offset_photos,
                )
            )
            reviews_task = self.location_reviews(
                LocationReviews(
                    locationId=location.location_id,
                    language=input.language,
                    limit=input.reviews_limit,
                    offset=input.offset_reviews,
                )
            )

            details, photos, reviews = await asyncio.gather(
                details_task, photos_task, reviews_task, return_exceptions=True
            )

            for label, value in (("details", details), ("photos", photos), ("reviews", reviews)):
                if isinstance(value, Exception):
                    result.error = f"{label} failed" if not result.error else f"{result.error}; {label} failed"
                else:
                    setattr(result, label, value)
            return result

        return await asyncio.gather(*(fetch_all(loc) for loc in locations))


def create_trip_advisor_client(settings: ApiSettings) -> TripAdvisor:
    """Instantiate the TripAdvisor client using project settings."""

    api_key = settings.ensure("trip_advisor_api_key")
    return TripAdvisor(api_key)


def create_trip_advisor_tools(client: TripAdvisor) -> Dict[str, Tool]:
    """Generate the LangChain tools backed by the TripAdvisor client."""

    async def location_search(params: dict[str, Any]) -> Any:
        return await client.search_location(SearchLocation(**params))

    async def location_details(params: dict[str, Any]) -> Any:
        return await client.location_details(LocationDetails(**params))

    async def location_photos(params: dict[str, Any]) -> Any:
        return await client.location_photos(LocationPhotos(**params))

    async def location_reviews(params: dict[str, Any]) -> Any:
        return await client.location_reviews(LocationReviews(**params))

    async def nearby_search(params: dict[str, Any]) -> Any:
        return await client.nearby_search(NearbySearch(**params))

    async def comprehensive(params: dict[str, Any]) -> Any:
        return await client.comprehensive_search(ComprehensiveLocationInput(**params))

    return {
        "location_search_tool": Tool.from_function(
            location_search,
            name="location_search_tool",
            description="Search TripAdvisor for matching locations.",
        ),
        "location_details_tool": Tool.from_function(
            location_details,
            name="location_details_tool",
            description="Fetch TripAdvisor details for a location ID.",
        ),
        "location_photos_tool": Tool.from_function(
            location_photos,
            name="location_photos_tool",
            description="Retrieve photos for a TripAdvisor location.",
        ),
        "location_reviews_tool": Tool.from_function(
            location_reviews,
            name="location_reviews_tool",
            description="Retrieve reviews for a TripAdvisor location.",
        ),
        "nearby_search_tool": Tool.from_function(
            nearby_search,
            name="nearby_search_tool",
            description="Return nearby places for a coordinate pair.",
        ),
        "comprehensive_search_tool": Tool.from_function(
            comprehensive,
            name="comprehensive_search_tool",
            description="Fetch TripAdvisor details, photos, and reviews in one call.",
        ),
    }
