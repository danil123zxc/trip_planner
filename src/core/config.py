"""Configuration helpers for API keys and environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ApiSettings:
    """Centralised container for the external service credentials."""

    openai_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    trip_advisor_api_key: Optional[str] = None
    rapid_api_key: Optional[str] = None
    amadeus_api_key: Optional[str] = None
    amadeus_api_secret: Optional[str] = None
    xai_api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ApiSettings":
        """Load settings from environment variables used in the notebook."""

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            trip_advisor_api_key=os.getenv("TRIP_ADVISOR_API"),
            rapid_api_key=os.getenv("RAPID_API_KEY"),
            amadeus_api_key=os.getenv("AMADEUS_API"),
            amadeus_api_secret=os.getenv("AMADEUS_SECRET"),
            xai_api_key=os.getenv("XAI_API_KEY"),
        )

    def ensure(self, field: str) -> str:
        """Return the requested field and fail fast if it is missing."""

        value = getattr(self, field)
        if not value:
            raise RuntimeError(f"Missing configuration value: {field}")
        return value

    def apply_langsmith_tracing(self) -> None:
        """Mirror the environment tweaks that were happening in the notebook."""

        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
        if self.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", self.openai_api_key)
        if self.tavily_api_key:
            os.environ.setdefault("TAVILY_API_KEY", self.tavily_api_key)
        if self.trip_advisor_api_key:
            os.environ.setdefault("TRIP_ADVISOR_API", self.trip_advisor_api_key)
        if self.rapid_api_key:
            os.environ.setdefault("RAPID_API_KEY", self.rapid_api_key)
