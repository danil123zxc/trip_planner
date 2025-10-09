"""Tavily internet search integration with RAG pipeline.

This module provides Tavily-powered internet search with document processing,
retrieval, and reranking for comprehensive web research in travel planning.

Public API:
    - create_internet_tool: Factory function to create internet search LangChain tool
    - process_pages: Utility to clean and process web page documents
    - InternetSearchInput: Pydantic schema for internet search parameters
"""
from src.services.tavily_search.tools import create_internet_tool
from src.services.tavily_search.client import process_pages
from src.services.tavily_search.schemas import InternetSearchInput

__all__ = [
    "create_internet_tool",
    "process_pages",
    "InternetSearchInput",
]

