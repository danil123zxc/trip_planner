"""Internet search helper built around the Tavily tools."""
from __future__ import annotations

import asyncio
import re
from typing import Any, List, Optional

from langchain_core.documents import Document
from langchain_core.tools import Tool
from langchain_tavily import TavilyExtract, TavilySearch
from pydantic import BaseModel, Field

from src.core.config import ApiSettings
from src.pipelines.rag import RetrievalPipeline


def process_pages(docs: List[Document]) -> List[Document]:
    """Clean Tavily documents by stripping links and noisy whitespace."""

    cleaned_docs: List[Document] = []
    for doc in docs:
        if not doc.page_content:
            continue
        text = doc.page_content
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"www\.\S+", "", text)
        text = re.sub(r"\n{2,}", "\n\n", text)
        text = re.sub(r"[ \t\u00a0]{2,}", " ", text)
        text = text.replace("\r", "")
        text = text.strip()
        if len(text) > 50:
            doc.page_content = text
            cleaned_docs.append(doc)
    return cleaned_docs


class InternetSearchInput(BaseModel):
    """Search parameters supported by the Tavily helper."""

    query: str = Field(description="Natural language query to research")
    country: str = Field(description="Two letter country code to influence Tavily results")
    search_depth: str = Field(default="basic", description="Depth of Tavily search (basic or advanced)")
    max_results: int = Field(default=5, description="Number of URLs to fetch")
    top_n: int = Field(default=10, description="Number of documents returned after reranking")
    k: int = Field(default=20, description="Number of documents to keep after FAISS prefilter")


def create_internet_tool(settings: ApiSettings, pipeline: RetrievalPipeline) -> Tool:
    """Return a LangChain `Tool` that executes the web search pipeline."""

    tavily_key = settings.ensure("tavily_api_key")

    async def _run(params: dict[str, Any]) -> List[Document]:
        data = InternetSearchInput(**params)
        tavily_search = TavilySearch(
            max_results=data.max_results,
            tavily_api_key=tavily_key,
            search_depth=data.search_depth,
            country=data.country,
        )
        tavily_extract = TavilyExtract()

        search_results = await tavily_search.ainvoke(data.query)
        urls = [item.get("url") for item in search_results.get("results", []) if item.get("url")]
        if not urls:
            return []

        extracted = await tavily_extract.ainvoke({"urls": urls})
        docs: List[Document] = [
            Document(page_content=item.get("raw_content"), metadata={"source": "tavily", "url": item.get("url")})
            for item in extracted.get("results", [])
        ]

        docs = process_pages(docs)
        if not docs:
            return []

        split_docs = await pipeline.split_docs(docs)
        filtered = await pipeline.prefilter(data.query, split_docs, k=data.k)
        if not filtered:
            return []

        save_task = pipeline.add_unique_documents(filtered)
        rerank_task = pipeline.rerank(data.query, filtered, top_n=data.top_n)
        _, reranked = await asyncio.gather(save_task, rerank_task)
        return reranked

    return Tool(
        name="search_internet",
        description="Search trusted web sources for destination research.",
        func=_run,
    )
