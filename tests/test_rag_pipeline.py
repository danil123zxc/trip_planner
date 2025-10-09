import pytest
from types import SimpleNamespace
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


@pytest.fixture()
def pipeline(monkeypatch):
    from src.pipelines import rag as rag_module

    class StubEmbeddings(Embeddings):
        def embed_documents(self, texts):
            return [[float(len(text))] for text in texts]

        async def aembed_documents(self, texts):
            return self.embed_documents(texts)

        def embed_query(self, text):
            return [float(len(text))]

        async def aembed_query(self, text):
            return self.embed_query(text)

    class StubRetriever:
        def __init__(self):
            self.documents = []

        async def ainvoke(self, query):
            return list(self.documents)

    class StubPrefilterStore:
        def __init__(self, docs):
            self.docs = list(docs)
            self.queries = []

        async def asimilarity_search_with_relevance_scores(self, query, k, **kwargs):
            self.queries.append(query)
            limited = self.docs[:k]
            return [(doc, 0.5) for doc in limited]

    class StubFAISS:
        last_prefilter_store = None

        def __init__(self, *args, **kwargs):
            self.index_to_docstore_id = {}
            self.saved_ids = []
            self.retriever = StubRetriever()

        def as_retriever(self, search_kwargs):
            return self.retriever

        async def aadd_texts(self, texts, ids=None):
            ids = ids or []
            for doc_id in ids:
                self.index_to_docstore_id[len(self.index_to_docstore_id)] = doc_id
                self.saved_ids.append(doc_id)
            return ids

        @classmethod
        async def afrom_documents(cls, docs, embeddings, **kwargs):
            store = StubPrefilterStore(docs)
            cls.last_prefilter_store = store
            return store

    class StubReranker:
        def __init__(self, model, top_n, **kwargs):
            self.top_n = top_n

        async def acompress_documents(self, docs, query):
            return list(docs)[: self.top_n]

    monkeypatch.setattr(rag_module, "FAISS", StubFAISS)
    monkeypatch.setattr(
        rag_module,
        "faiss",
        SimpleNamespace(IndexHNSWFlat=lambda *args, **kwargs: object(), METRIC_INNER_PRODUCT=0),
    )
    monkeypatch.setattr(rag_module, "CrossEncoderReranker", StubReranker)
    monkeypatch.setattr(rag_module, "HuggingFaceCrossEncoder", lambda model_name: object())

    StubFAISS.last_prefilter_store = None
    embeddings = StubEmbeddings()
    pipeline = rag_module.RetrievalPipeline(
        embeddings,
        retriever_k=3,
        cross_encoder_model="stub",
        chunk_size=50,
        chunk_overlap=0,
        embedding_dimension=4,
    )
    pipeline._faiss_class = StubFAISS
    pipeline._retriever.documents = []
    return pipeline


@pytest.mark.asyncio
async def test_split_docs_generates_chunks(pipeline):
    doc = Document(page_content="Sample text " * 100)
    chunks = await pipeline.split_docs([doc])
    assert len(chunks) > 1
    assert all(isinstance(chunk, Document) for chunk in chunks)


@pytest.mark.asyncio
async def test_add_unique_documents_skips_duplicates(pipeline):
    docs = [
        Document(page_content="alpha"),
        Document(page_content="beta"),
        Document(page_content="alpha"),
    ]
    first = await pipeline.add_unique_documents(docs)
    assert len(first) == 2
    second = await pipeline.add_unique_documents([Document(page_content="alpha")])
    assert second == []


@pytest.mark.asyncio
async def test_prefilter_limits_results_and_tracks_query(pipeline):
    docs = [Document(page_content=f"doc-{i}") for i in range(4)]
    filtered = await pipeline.prefilter("weekend trip", docs, k=2)
    assert len(filtered) == 2
    store = pipeline._faiss_class.last_prefilter_store
    assert store is not None
    assert store.queries == ["weekend trip"]


@pytest.mark.asyncio
async def test_rerank_truncates_to_requested_top_n(pipeline):
    docs = [Document(page_content=f"doc-{i}") for i in range(5)]
    reranked = await pipeline.rerank("budget ideas", docs, top_n=2)
    assert len(reranked) == 2


@pytest.mark.asyncio
async def test_search_db_runs_full_flow(pipeline):
    pipeline._retriever.documents = [Document(page_content=f"doc-{i}") for i in range(3)]
    results = await pipeline.search_db("family holiday", top_n=2, prefilter_k=2)
    assert len(results) == 2
    assert len(pipeline._vector_store.saved_ids) == 2

@pytest.mark.asyncio
async def test_search_db_tool_enforces_structured_payload(pipeline):
    tool = pipeline.as_tool()
    
    pipeline._retriever.documents = [
        Document(page_content="museum list"), 
        Document(page_content="budget tips")
    ]
    output = await tool.ainvoke({"query": "tokyo activities", "top_n": 1, "k": 1})
    assert len(output) == 1
    assert isinstance(output[0], Document)

