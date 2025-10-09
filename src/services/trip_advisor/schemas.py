from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from pydantic.types import Literal
from src.core.types import ISO4217, HttpURLStr, Lat, Lon, Rating


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
