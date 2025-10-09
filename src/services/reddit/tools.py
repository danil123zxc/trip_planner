from src.core.config import ApiSettings
from src.services.reddit.schemas import RedditSearchInput
from src.services.reddit.client import parse_reddit_results
from src.pipelines.rag import RetrievalPipeline
from langchain_core.documents import Document
from langchain_core.tools import Tool, StructuredTool
from typing import List
import asyncio
from langchain_community.tools.reddit_search.tool import (
    RedditSearchRun,
    RedditSearchSchema,
)
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper

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

    async def _arun(**kwargs) -> List[Document]:
        data = RedditSearchInput(**kwargs)
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

    return StructuredTool.from_function(
        coroutine=_arun,
        name="search_reddit",
        description=reddit_search.description or "Search Reddit",
        args_schema=RedditSearchInput,
    )
