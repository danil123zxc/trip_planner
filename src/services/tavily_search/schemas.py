from pydantic import BaseModel, Field

class InternetSearchInput(BaseModel):
    """Search parameters supported by the Tavily helper."""

    query: str = Field(description="Natural language query to research")
    country: str = Field(description="Two letter country code to influence Tavily results")
    search_depth: str = Field(default="basic", description="Depth of Tavily search (basic or advanced)")
    max_results: int = Field(default=5, description="Number of URLs to fetch")
    top_n: int = Field(default=10, description="Number of documents returned after reranking")
    k: int = Field(default=20, description="Number of documents to keep after FAISS prefilter")
