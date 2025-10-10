from pydantic import BaseModel, Field
from typing import Optional

class InternetSearchInput(BaseModel):
    """Search parameters supported by the Tavily helper."""

    query: str = Field(description="Natural language query to research")
    country: Optional[str] = Field(default=None, description="Country name to influence Tavily results ex. japan")
    search_depth: Optional[str] = Field(default="basic", description="Depth of Tavily search (basic or advanced)")
    max_results: Optional[int] = Field(default=5, description="Number of URLs to fetch")
    top_n: Optional[int] = Field(default=10, description="Number of documents returned after reranking")
    k: Optional[int] = Field(default=20, description="Number of documents to keep after FAISS prefilter")
