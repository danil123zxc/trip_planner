"""Tests for service modules."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx

from src.services.geocoding import get_coordinates_nominatim
from src.services.trip_advisor import (
    TripAdvisor,
    SearchLocation,
    LocationDetails,
    LocationPhotos,
    LocationReviews,
    NearbySearch,
    ComprehensiveLocationInput,
)


@patch('src.services.geocoding.requests.get')
def test_get_coordinates_nominatim_success(mock_get):
    """Test successful geocoding request."""
    # Mock successful response
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "lat": "35.6895",
            "lon": "139.6917",
            "display_name": "Tokyo, Japan"
        }
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_coordinates_nominatim("Tokyo, Japan")
    assert result == "35.6895,139.6917"
    mock_get.assert_called_once()


@patch('src.services.geocoding.requests.get')
def test_get_coordinates_nominatim_no_results(mock_get):
    """Test geocoding with no results."""
    # Mock empty response
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_coordinates_nominatim("Nonexistent Place")
    assert result is None


@patch('src.services.geocoding.requests.get')
def test_get_coordinates_nominatim_api_error(mock_get):
    """Test geocoding with API error."""
    # Mock API error
    mock_get.side_effect = Exception("API Error")

    result = get_coordinates_nominatim("Tokyo, Japan")
    assert result is None


@patch('src.services.geocoding.requests.get')
def test_get_coordinates_nominatim_invalid_input(mock_get):
    """Test geocoding with invalid input."""
    # Mock empty response for empty string
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = get_coordinates_nominatim("")
    assert result is None
    
    # Mock error for None input
    mock_get.side_effect = Exception("Invalid input")
    result = get_coordinates_nominatim(None)
    assert result is None


# TripAdvisor Tests
class TestTripAdvisor:
    """Test suite for the TripAdvisor client."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTPX client for testing."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        return mock_client

    @pytest.fixture
    def tripadvisor_client(self, mock_client):
        """Create a TripAdvisor client with mocked HTTP client."""
        with patch('httpx.AsyncClient', return_value=mock_client):
            client = TripAdvisor(api_key="test-key")
            client._client = mock_client
            return client

    async def test_init_with_defaults(self):
        """Test TripAdvisor initialization with default parameters."""
        with patch('httpx.AsyncClient') as mock_httpx:
            client = TripAdvisor(api_key="test-key")
            mock_httpx.assert_called_once()
            assert client.api_key == "test-key"
            assert client.api_url == "https://api.content.tripadvisor.com/api/v1/location"

    async def test_init_with_custom_params(self):
        """Test TripAdvisor initialization with custom parameters."""
        with patch('httpx.AsyncClient') as mock_httpx:
            client = TripAdvisor(
                api_key="custom-key",
                base_url="https://custom.api.com/v2",
                timeout_s=30.0
            )
            mock_httpx.assert_called_once()
            assert client.api_key == "custom-key"
            assert client.api_url == "https://custom.api.com/v2/location"

    async def test_search_location_success(self, tripadvisor_client, mock_client):
        """Test successful location search."""
        # Mock successful API response
        mock_response = Mock()  # Use Mock, not AsyncMock - httpx Response is sync
        mock_response.json.return_value = {
            "data": [
                {
                    "location_id": "123456",
                    "name": "Test Restaurant",
                    "address_obj": {
                        "address_string": "123 Test St, Tokyo, Japan",
                        "country": "Japan",
                        "city": "Tokyo"
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        search_input = SearchLocation(searchQuery="restaurants in Tokyo")
        result = await tripadvisor_client.search_location(search_input)

        assert len(result.data) == 1
        assert result.data[0].location_id == "123456"
        assert result.data[0].name == "Test Restaurant"
        mock_client.get.assert_called_once()

    async def test_search_location_empty_results(self, tripadvisor_client, mock_client):
        """Test location search with no results."""
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        search_input = SearchLocation(searchQuery="nonexistent place")
        result = await tripadvisor_client.search_location(search_input)

        assert len(result.data) == 0

    async def test_location_details_success(self, tripadvisor_client, mock_client):
        """Test successful location details retrieval."""
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {
            "location_id": "123456",
            "name": "Test Restaurant",
            "description": "A great restaurant",
            "web_url": "https://tripadvisor.com/restaurant/123456",
            "address_obj": {
                "address_string": "123 Test St, Tokyo, Japan",
                "country": "Japan"
            },
            "latitude": 35.6762,  
            "longitude": 139.6503,  
            "website": "https://test-restaurant.com",
            "rating": 4.5,  
            "price_level": "$$"
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        details_input = LocationDetails(locationId="123456")
        result = await tripadvisor_client.location_details(details_input)

        assert result.location_id == "123456"
        assert result.name == "Test Restaurant"
        assert result.description == "A great restaurant"
        assert result.rating == 4.5  
        assert result.price_level == "$$"

    async def test_location_photos_success(self, tripadvisor_client, mock_client):
        """Test successful location photos retrieval."""
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {
            "data": [
                {
                    "caption": "Beautiful exterior",
                    "published_date": "2023-01-01",
                    "images": {
                        "original": {
                            "height": 800,
                            "width": 1200,
                            "url": "https://example.com/photo1.jpg"
                        }
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        photos_input = LocationPhotos(locationId="123456")
        result = await tripadvisor_client.location_photos(photos_input)

        assert len(result.data) == 1
        assert result.data[0].caption == "Beautiful exterior"
        assert result.data[0].image.url == "https://example.com/photo1.jpg"
        assert result.data[0].image.height == 800

    async def test_location_reviews_success(self, tripadvisor_client, mock_client):
        """Test successful location reviews retrieval."""
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {
            "data": [
                {
                    "lang": "en",
                    "published_date": "2023-01-01",
                    "rating": 5,
                    "url": "https://tripadvisor.com/review/1",
                    "text": "Great food and service!",
                    "title": "Amazing experience",
                    "trip_type": "Couples",
                    "travel_date": "2023-01-01"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        reviews_input = LocationReviews(locationId="123456")
        result = await tripadvisor_client.location_reviews(reviews_input)

        assert len(result.data) == 1
        assert result.data[0].rating == 5
        assert result.data[0].text == "Great food and service!"
        assert result.data[0].title == "Amazing experience"

    async def test_nearby_search_success(self, tripadvisor_client, mock_client):
        """Test successful nearby search."""
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {
            "data": [
                {
                    "location_id": "123456",
                    "name": "Nearby Restaurant",
                    "distance": "0.5 km",
                    "bearing": "N",
                    "address_obj": {
                        "address_string": "456 Nearby St, Tokyo, Japan",
                        "country": "Japan"
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        nearby_input = NearbySearch(
            latLong="35.6762,139.6503",
            category="restaurants",
            radius=1,
            radiusUnit="km"
        )
        result = await tripadvisor_client.nearby_search(nearby_input)

        assert len(result.data) == 1
        assert result.data[0].location_id == "123456"
        assert result.data[0].name == "Nearby Restaurant"
        assert result.data[0].distance == "0.5 km"

    async def test_comprehensive_search_success(self, tripadvisor_client, mock_client):
        """Test successful comprehensive search."""
        # Mock search results
        search_response = Mock()  # httpx Response methods are sync
        search_response.json.return_value = {
            "data": [
                {
                    "location_id": "123456",
                    "name": "Test Restaurant",
                    "address_obj": {
                        "address_string": "123 Test St, Tokyo, Japan",
                        "country": "Japan"
                    }
                }
            ]
        }
        search_response.raise_for_status.return_value = None

        # Mock details response
        details_response = Mock()  # httpx Response methods are sync
        details_response.json.return_value = {
            "location_id": "123456",
            "name": "Test Restaurant",
            "rating": 4.5,  # float, not string
            "price_level": "$$"
        }
        details_response.raise_for_status.return_value = None

        # Mock photos response
        photos_response = Mock()  # httpx Response methods are sync
        photos_response.json.return_value = {"data": []}
        photos_response.raise_for_status.return_value = None

        # Mock reviews response
        reviews_response = Mock()  # httpx Response methods are sync
        reviews_response.json.return_value = {"data": []}
        reviews_response.raise_for_status.return_value = None

        # Set up mock client to return different responses for different calls
        mock_client.get.side_effect = [
            search_response,  # search_location call
            details_response,  # location_details call
            photos_response,   # location_photos call
            reviews_response   # location_reviews call
        ]

        comprehensive_input = ComprehensiveLocationInput(
            searchQuery="restaurants in Tokyo",
            limit_locations=1
        )
        result = await tripadvisor_client.comprehensive_search(comprehensive_input)

        assert len(result) == 1
        assert result[0].location_id == "123456"
        assert result[0].name == "Test Restaurant"
        assert result[0].details is not None
        assert result[0].photos is not None
        assert result[0].reviews is not None

    async def test_comprehensive_search_no_results(self, tripadvisor_client, mock_client):
        """Test comprehensive search with no search results."""
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        comprehensive_input = ComprehensiveLocationInput(
            searchQuery="nonexistent place"
        )
        result = await tripadvisor_client.comprehensive_search(comprehensive_input)

        assert len(result) == 0

    async def test_api_error_handling(self, tripadvisor_client, mock_client):
        """Test API error handling."""
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "API Error", request=Mock(), response=Mock()
        )

        search_input = SearchLocation(searchQuery="test")
        
        with pytest.raises(httpx.HTTPStatusError):
            await tripadvisor_client.search_location(search_input)

    async def test_context_manager_usage(self):
        """Test TripAdvisor as async context manager."""
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.return_value = mock_client
            
            async with TripAdvisor(api_key="test-key") as client:
                assert isinstance(client, TripAdvisor)
                assert client.api_key == "test-key"
            
            # Verify client was closed
            mock_client.aclose.assert_called_once()

    async def test_close_method(self, tripadvisor_client, mock_client):
        """Test explicit client closure."""
        await tripadvisor_client.aclose()
        mock_client.aclose.assert_called_once()

    async def test_parameter_passing(self, tripadvisor_client, mock_client):
        """Test that parameters are correctly passed to API calls."""
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        search_input = SearchLocation(
            searchQuery="restaurants",
            category="restaurants",
            radius=5,
            radiusUnit="km",
            language="en"
        )
        await tripadvisor_client.search_location(search_input)

        # Verify the API call was made with correct parameters
        call_args = mock_client.get.call_args
        assert "search" in call_args[0][0]  # URL contains 'search'
        params = call_args[1]["params"]
        assert params["key"] == "test-key"
        assert params["searchQuery"] == "restaurants"
        assert params["category"] == "restaurants"
        assert params["radius"] == 5
        assert params["radiusUnit"] == "km"
        assert params["language"] == "en"

    async def test_photos_with_missing_images(self, tripadvisor_client, mock_client):
        """Test photos handling when images data is missing."""
        mock_response = Mock()  # httpx Response methods are sync
        mock_response.json.return_value = {
            "data": [
                {
                    "caption": "Photo without images",
                    "published_date": "2023-01-01"
                    # Missing "images" field
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        photos_input = LocationPhotos(locationId="123456")
        result = await tripadvisor_client.location_photos(photos_input)

        assert len(result.data) == 1
        assert result.data[0].caption == "Photo without images"
        assert result.data[0].image is not None
        assert result.data[0].image.url is None

    async def test_reviews_with_missing_fields(self, tripadvisor_client, mock_client):
        """Test reviews handling when some optional fields are missing."""
        mock_response = Mock()  
        mock_response.json.return_value = {
            "data": [
                {
                    "lang": "en",  # Required field
                    "published_date": "2023-01-01",  # Required field
                    "rating": 4,
                    "text": "Good food"
                    # Missing optional fields: title, url, trip_type, travel_date
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        reviews_input = LocationReviews(locationId="123456")
        result = await tripadvisor_client.location_reviews(reviews_input)

        assert len(result.data) == 1
        assert result.data[0].rating == 4
        assert result.data[0].text == "Good food"
        assert result.data[0].lang == "en"
        assert result.data[0].published_date == "2023-01-01"
        assert result.data[0].title is None  # Optional field not provided
        assert result.data[0].url is None  # Optional field not provided


class TestTripAdvisorTools:
    """Test suite for TripAdvisor LangChain tools."""

    def test_comprehensive_tool_with_dict_params(self):
        """Test comprehensive tool handles dictionary parameters correctly."""
        from src.services.trip_advisor import create_trip_advisor_tools
        
        # Mock client - spec ensures it has the right interface
        mock_client = AsyncMock(spec=TripAdvisor)
        mock_client.comprehensive_search.return_value = []
        
        tools = create_trip_advisor_tools(mock_client)
        comprehensive_tool = tools["comprehensive_search_tool"]
        
        # Test with dictionary parameter (LangChain StructuredTool expects dict/object, not string)
        result = comprehensive_tool.invoke({"searchQuery": "restaurants in Tokyo"})
        
        # Verify the result
        assert result == []
        
        # Verify the client was called with proper parameters
        mock_client.comprehensive_search.assert_called_once()
        # Get the actual ComprehensiveLocationInput object that was passed
        call_args = mock_client.comprehensive_search.call_args
        input_obj = call_args[0][0] if call_args[0] else call_args[1].get('input')
        assert input_obj.searchQuery == "restaurants in Tokyo"

    def test_comprehensive_tool_with_multiple_params(self):
        """Test comprehensive tool handles multiple parameters correctly."""
        from src.services.trip_advisor import create_trip_advisor_tools
        
        # Mock client
        mock_client = AsyncMock(spec=TripAdvisor)
        mock_client.comprehensive_search.return_value = []
        
        tools = create_trip_advisor_tools(mock_client)
        comprehensive_tool = tools["comprehensive_search_tool"]
        
        # Test with dictionary containing multiple parameters
        params_dict = {"searchQuery": "hotels in Paris", "limit_locations": 3}
        
        result = comprehensive_tool.invoke(params_dict)
        
        # Verify the result
        assert result == []
        
        # Verify the client was called with proper parameters
        mock_client.comprehensive_search.assert_called_once()
        call_args = mock_client.comprehensive_search.call_args
        input_obj = call_args[0][0] if call_args[0] else call_args[1].get('input')
        assert input_obj.searchQuery == "hotels in Paris"
        assert input_obj.limit_locations == 3

    def test_comprehensive_tool_with_all_comprehensive_params(self):
        """Test comprehensive tool with all ComprehensiveLocationInput parameters."""
        from src.services.trip_advisor import create_trip_advisor_tools
        
        # Mock client
        mock_client = AsyncMock(spec=TripAdvisor)
        mock_client.comprehensive_search.return_value = []
        
        tools = create_trip_advisor_tools(mock_client)
        comprehensive_tool = tools["comprehensive_search_tool"]
        
        # Test with all possible parameters (without __arg1)
        all_params = {
            "searchQuery": "Cultural activities in Tokyo",
            "latLong": "35.6762,139.6503",
            "category": "attractions",
            "phone": "+81-3-1234-5678",
            "address": "Tokyo, Japan",
            "radius": 5,
            "radiusUnit": "km",
            "language": "en",
            "limit_locations": 3,
            "photos_limit": 15,
            "reviews_limit": 20,
            "currency": "USD",
            "offset_photos": 0,
            "offset_reviews": 0
        }
        
        result = comprehensive_tool.invoke(all_params)
        
        # Verify the result
        assert result == []
        
        # Verify the client was called with all parameters
        mock_client.comprehensive_search.assert_called_once()
        call_args = mock_client.comprehensive_search.call_args
        input_obj = call_args[0][0] if call_args[0] else call_args[1].get('input')
        assert input_obj.searchQuery == "Cultural activities in Tokyo"
        assert input_obj.latLong == "35.6762,139.6503"
        assert input_obj.category == "attractions"
        assert input_obj.phone == "+81-3-1234-5678"
        assert input_obj.address == "Tokyo, Japan"
        assert input_obj.radius == 5
        assert input_obj.radiusUnit == "km"
        assert input_obj.language == "en"
        assert input_obj.limit_locations == 3
        assert input_obj.photos_limit == 15
        assert input_obj.reviews_limit == 20
        assert input_obj.currency == "USD"
        assert input_obj.offset_photos == 0
        assert input_obj.offset_reviews == 0
