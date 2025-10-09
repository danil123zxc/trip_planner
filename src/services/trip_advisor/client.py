from src.core.config import ApiSettings
import httpx
from typing import Dict, Any, List
from src.services.trip_advisor.schemas import SearchLocation, LocationOutput, LocationData, Address, LocationDetails, DetailsOutput, LocationPhotos, PhotosOutput, PhotosData, Image, LocationReviews, ReviewOutput, ReviewData, NearbySearch, NearbySearchOutput, NearbySearchData, ComprehensiveLocationInput, ComprehensiveLocationResult
import asyncio


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