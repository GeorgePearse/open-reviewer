"""Embedding-based semantic search for code."""

from review_eval.semantic.embeddings.chunker import chunk_code, chunk_python_file
from review_eval.semantic.embeddings.client import EmbeddingClient
from review_eval.semantic.embeddings.vector_store import VectorStore

__all__ = [
    "EmbeddingClient",
    "VectorStore",
    "chunk_code",
    "chunk_python_file",
]
