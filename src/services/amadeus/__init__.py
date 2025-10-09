"""Amadeus flight search API integration.

This module provides client and tool factories for integrating Amadeus flight search
into LangChain-based travel planning workflows.

Public API:
    - create_amadeus_client: Factory function to create Amadeus client
    - create_flight_search_tool: Factory function to create flight search LangChain tool
    - FlightSearchInput: Pydantic schema for flight search parameters
"""
from src.services.amadeus.client import create_amadeus_client
from src.services.amadeus.tools import create_flight_search_tool
from src.services.amadeus.schemas import FlightSearchInput

__all__ = [
    "create_amadeus_client",
    "create_flight_search_tool",
    "FlightSearchInput",
]

