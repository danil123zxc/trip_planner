from src.core.config import ApiSettings
from src.services.tavily_search.schemas import InternetSearchInput
from src.services.tavily_search.client import process_pages
from src.pipelines.rag import RetrievalPipeline
from langchain_core.documents import Document
from langchain_core.tools import Tool, StructuredTool
from typing import List
import asyncio
from langchain_tavily import TavilySearch, TavilyExtract


def create_internet_tool(settings: ApiSettings, pipeline: RetrievalPipeline) -> Tool:
    """Return a LangChain `Tool` that executes the web search pipeline."""

    tavily_key = settings.ensure("tavily_api_key")


    async def _arun(**kwargs) -> List[Document]:
        
        data = InternetSearchInput(**kwargs)
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
        
          
    return StructuredTool.from_function(
        coroutine=_arun,
        name="search_internet_tool",
        description="Search trusted web sources for destination research.",
        args_schema=InternetSearchInput,
    )
