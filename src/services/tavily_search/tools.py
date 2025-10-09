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
        """Execute the complete web search and RAG pipeline.
        
        This function performs a multi-stage process:
        1. Searches the web using Tavily API
        2. Extracts full content from discovered URLs
        3. Processes and cleans the extracted pages
        4. Splits documents into chunks for better retrieval
        5. Pre-filters chunks using vector similarity (FAISS)
        6. Reranks filtered chunks using cross-encoder
        7. Persists unique documents to the vector store
        
        Args:
            **kwargs: Keyword arguments validated against InternetSearchInput schema:
                - query (str): Natural language search query
                - country (str): Two letter country code to influence results
                - search_depth (str): 'basic' or 'advanced' search mode
                - max_results (int): Number of URLs to fetch from search
                - k (int): Number of chunks to keep after FAISS pre-filtering
                - top_n (int): Number of final documents to return after reranking
        
        Returns:
            List[Document]: Reranked documents with page_content and metadata.
                Returns empty list if no results found at any stage.
        
        Note:
            Document persistence and reranking happen concurrently using asyncio.gather
            for optimal performance.
        """

        payload = InternetSearchInput(**kwargs)
        tavily_search = TavilySearch(
            max_results=payload.max_results,
            tavily_api_key=tavily_key,
            search_depth=payload.search_depth,
            country=payload.country,
        )
        tavily_extract = TavilyExtract()

        search_results = await tavily_search.ainvoke(payload.query)
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
        filtered = await pipeline.prefilter(payload.query, split_docs, k=payload.k)
        if not filtered:
            return []

        save_task = pipeline.add_unique_documents(filtered)
        rerank_task = pipeline.rerank(payload.query, filtered, top_n=payload.top_n)
        _, reranked = await asyncio.gather(save_task, rerank_task)
        return reranked
        
          
    return StructuredTool.from_function(
        coroutine=_arun,
        name="search_internet_tool",
        description="Search trusted web sources for destination research.",  
        args_schema=InternetSearchInput,
    )