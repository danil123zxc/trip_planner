"""Tests for service modules."""
from __future__ import annotations

import pytest
from unittest.mock import Mock, patch

from src.services.geocoding import get_coordinates_nominatim


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
