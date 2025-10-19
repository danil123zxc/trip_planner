from pydantic import BaseModel, Field
from typing import Optional

class RedditSearchInput(BaseModel):
    """Parameters accepted by the Reddit tool."""

    query: str = Field(description="Keyword query to send to Reddit search")
    time_filter: str = Field(
        description="Time filter for search (year, week, month, all, day, hour)",
        default="week",
    )
    sort: str = Field(
        description="Sorting strategy (relevance, hot, top, new, comments)",
        default="relevance",
    )
    subreddit: Optional[str] = Field(default="all", description="Subreddit to scope into examples: travel, travelplanning, traveladvice")
    limit: int = Field(default=20, description="Number of raw reddit posts to fetch")
    top_n: int = Field(default=10, description="Number of documents returned after reranking")
    k: int = Field(default=20, description="Number of documents to keep after FAISS prefilter")
