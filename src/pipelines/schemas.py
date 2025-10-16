from pydantic import BaseModel
from dataclasses import dataclass
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

class SearchDBInput(BaseModel):
    query: str
    top_n: int = 10
    k: int = 20


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
