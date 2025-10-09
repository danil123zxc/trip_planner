"""Geocoding and location resolution services.

This module provides geocoding functionality for converting addresses to coordinates
and vice versa using the Nominatim OpenStreetMap API.

Public API:
    - get_coordinates_nominatim: Function to convert address to coordinates
"""
from src.services.geocoding.geocoding import get_coordinates_nominatim

__all__ = [
    "get_coordinates_nominatim",
]

