"""Asynchronous retrieval utilities extracted from the original notebook.

This module concentrates the document splitting, vector-store management,
FAISS-backed prefiltering, and cross-encoder reranking logic that was scattered
across the prototype notebook.  Everything is wrapped in `RetrievalPipeline`
so it can be reused from agents, tools, or CLI workflows without relying on
notebook globals.
"""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Iterable, List, Optional

import faiss
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.tools import Tool
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass(slots=True)
class RetrievalConfig:
    """Configuration parameters required to build a retrieval pipeline."""

    openai_api_key: str
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1024
    cross_encoder_model: str = "BAAI/bge-reranker-base"
    retriever_k: int = 20

    def build_embeddings(self) -> Embeddings:
        """Return a LangChain embeddings instance using the configured model."""

        return OpenAIEmbeddings(
            api_key=self.openai_api_key,
            model=self.embedding_model,
            dimensions=self.embedding_dimensions,
        )


class RetrievalPipeline:
    """Container that exposes splitting, vector storage, and reranking helpers."""

    def __init__(
        self,
        embeddings: Embeddings,
        *,
        retriever_k: int = 20,
        cross_encoder_model: str = "BAAI/bge-reranker-base",
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        embedding_dimension: int = 1024,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                r"\n{2,}",
                r"\n#{1,6}\s",
                "\n\n",
                "\n",
                " ",
                "",
                "!",
                "?",
                ".",
                "\t",
            ],
        )
        self._embeddings = embeddings
        self._vector_store = FAISS(
            index=faiss.IndexHNSWFlat(
                embedding_dimension,
                32,
                faiss.METRIC_INNER_PRODUCT,
            ),
            docstore=InMemoryDocstore(),
            embedding_function=embeddings,
            index_to_docstore_id={},
            relevance_score_fn=lambda d: float(1.0 / (1.0 + float(d))),
            normalize_L2=True,
        )
        self._retriever = self._vector_store.as_retriever(search_kwargs={"k": retriever_k})
        self._reranker = CrossEncoderReranker(
            model=HuggingFaceCrossEncoder(model_name=cross_encoder_model),
            top_n=retriever_k,
        )

    @property
    def retriever(self):
        """Expose the underlying LangChain retriever."""

        return self._retriever

    async def split_docs(self, docs: Iterable[Document]) -> List[Document]:
        """Split documents into overlapping chunks using the configured splitter."""

        docs = list(docs)
        if not docs:
            return []
        return await self._splitter.atransform_documents(docs)

    async def add_unique_documents(self, docs: Iterable[Document]) -> List[str]:
        """Add only new documents to the FAISS store based on a SHA-256 hash."""

        docs = list(docs)
        if not docs:
            return []

        unique_texts: dict[str, str] = {}
        for doc in docs:
            doc_id = hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()
            if doc_id not in self._vector_store.index_to_docstore_id.values():
                unique_texts[doc.page_content] = doc_id

        if not unique_texts:
            return []

        return await self._vector_store.aadd_texts(
            list(unique_texts.keys()), ids=list(unique_texts.values())
        )

    async def prefilter(self, query: str, docs: Iterable[Document], *, k: int = 20) -> List[Document]:
        """Run a quick FAISS similarity search across the provided documents."""

        docs = list(docs)
        if not docs:
            return []

        filtered_store = await FAISS.afrom_documents(docs, 
                                                    self._embeddings, 
                                                    normalize_L2=True, 
                                                    relevance_score_fn=lambda d: float(1.0 / (1.0 + float(d))))
                                                    
        score_threshold = {"score_threshold": 0.3}        

        filtered_docs = await filtered_store.asimilarity_search_with_relevance_scores(query, k=k, **score_threshold)
        return [doc for doc, _ in filtered_docs]

    async def rerank(
        self,
        query: str,
        docs: Iterable[Document],
        *,
        top_n: Optional[int] = None,
    ) -> List[Document]:
        """Use the cross-encoder reranker to score and truncate the document list."""

        docs = list(docs)
        if not docs:
            return []

        reranked = await self._reranker.acompress_documents(docs, query)
        if top_n is not None:
            return reranked[:top_n]
        return reranked

    async def search_db(
        self,
        query: str,
        *,
        top_n: int = 10,
        prefilter_k: int = 20,
    ) -> List[Document]:
        """Retrieve, prefilter, rerank, and persist documents for a query."""

        documents = await self._retriever.ainvoke(query)
        filtered = await self.prefilter(query, documents, k=prefilter_k)
        if not filtered:
            return []

        save_task = self.add_unique_documents(filtered)
        rerank_task = self.rerank(query, filtered, top_n=top_n)
        _, reranked = await asyncio.gather(save_task, rerank_task)
        return reranked

    def as_tool(self, *, name: str = "search_db", description: Optional[str] = None) -> Tool:
        """Expose the search pipeline as a LangChain retriever tool."""

        description = description or "Search the persisted vector store for trip research."

        async def _run(params) -> List[Document]:  # type: ignore[override]
            top_n = params.get("top_n", 10)
            k = params.get("k", 20)
            return await self.search_db(params["query"], top_n=top_n, prefilter_k=k)

        return Tool(
            name=name,
            description=description,
            func=_run,
        )


def create_default_pipeline(config: RetrievalConfig) -> RetrievalPipeline:
    """Factory that assembles a retrieval pipeline from the provided settings."""

    embeddings = config.build_embeddings()
    return RetrievalPipeline(
        embeddings,
        retriever_k=config.retriever_k,
        cross_encoder_model=config.cross_encoder_model,
        embedding_dimension=config.embedding_dimensions,
    )
