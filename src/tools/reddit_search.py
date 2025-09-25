"""Reddit search tooling wired up for asynchronous LangChain agents."""
from __future__ import annotations

import asyncio
import re
from typing import Any, List, Optional

from langchain_community.tools.reddit_search.tool import (
    RedditSearchRun,
    RedditSearchSchema,
)
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper
from langchain_core.documents import Document
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

from src.core.config import ApiSettings
from src.pipelines.rag import RetrievalPipeline


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
    subreddit: Optional[str] = Field(default="all", description="Subreddit to scope into")
    limit: int = Field(default=20, description="Number of raw reddit posts to fetch")
    top_n: int = Field(default=10, description="Number of documents returned after reranking")
    k: int = Field(default=20, description="Number of documents to keep after FAISS prefilter")


def parse_reddit_results(payload: Any) -> List[Document]:
    """Normalise the Reddit string payload into Documents for downstream tools."""

    post_pattern = re.compile(
        r"""
        Post\ Title:\s*(?P<title>.*?)\n
        \s*User:\s*(?P<user>.*?)\n
        \s*Subreddit:\s*(?P<subreddit>.*?)\s*:?\s*\n
        \s*Text\ body:\s*(?P<body>.*?)
        \s*Post\ URL:\s*(?P<url>\S+)\n
        \s*Post\ Category:\s*(?P<category>.*?)\.\s*\n
        \s*Score:\s*(?P<score>\d+)
        """,
        re.DOTALL | re.VERBOSE,
    )

    text = payload.get("result") if isinstance(payload, dict) and "result" in payload else payload
    if not isinstance(text, str):
        return []

    documents: List[Document] = []
    for match in post_pattern.finditer(text):
        title = match.group("title").strip().strip("'\"")
        user = match.group("user").strip()
        subreddit = match.group("subreddit").strip().rstrip(":")
        body = match.group("body").strip()
        url = match.group("url").strip()
        category = match.group("category").strip()
        score = match.group("score").strip()

        page_content = f"{title}\n\n{body}".strip() or url
        page_content = re.sub(r"https?://\S+", "", page_content)

        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "source": "reddit",
                    "title": title,
                    "url": url,
                    "subreddit": subreddit,
                    "author": user,
                    "category": category,
                    "score": int(score) if score.isdigit() else None,
                },
            )
        )
    return documents


def create_reddit_tool(settings: ApiSettings, pipeline: RetrievalPipeline) -> Tool:
    """Return an async tool that mirrors the prototype reddit search workflow."""

    client_id = settings.ensure("reddit_client_id")
    client_secret = settings.ensure("reddit_client_secret")

    api_wrapper = RedditSearchAPIWrapper(
        reddit_client_id=client_id,
        reddit_client_secret=client_secret,
        reddit_user_agent="langchain_reddit_bot/0.1",
    )

    reddit_search = RedditSearchRun(
        api_wrapper=api_wrapper,
        description="Search Reddit for travel insights and return reranked documents.",
    )

    async def _run(params: dict[str, Any]) -> List[Document]:
        data = RedditSearchInput(**params)
        raw_payload = await reddit_search.arun(
            RedditSearchSchema(
                query=data.query,
                sort=data.sort,
                time_filter=data.time_filter,
                subreddit=data.subreddit,
                limit=str(data.limit),
            ).model_dump()
        )
        documents = parse_reddit_results(raw_payload)
        if not documents:
            return []

        split_docs = await pipeline.split_docs(documents)
        filtered = await pipeline.prefilter(data.query, split_docs, k=data.k)
        if not filtered:
            return []

        save_task = pipeline.add_unique_documents(filtered)
        rerank_task = pipeline.rerank(data.query, filtered, top_n=data.top_n)
        _, reranked = await asyncio.gather(save_task, rerank_task)
        return reranked

    return Tool(
        name="search_reddit",
        description=reddit_search.description or "Search Reddit",
        coroutine=_run,
    )
