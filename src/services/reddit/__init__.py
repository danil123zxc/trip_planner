"""Reddit search integration with RAG pipeline.

This module provides Reddit search functionality with document parsing,
retrieval, and reranking for travel research workflows.

Public API:
    - create_reddit_tool: Factory function to create Reddit search LangChain tool
    - parse_reddit_results: Utility to parse Reddit API responses into Documents
    - RedditSearchInput: Pydantic schema for Reddit search parameters
"""
from src.services.reddit.tools import create_reddit_tool
from src.services.reddit.client import parse_reddit_results
from src.services.reddit.schemas import RedditSearchInput

__all__ = [
    "create_reddit_tool",
    "parse_reddit_results",
    "RedditSearchInput",
]

