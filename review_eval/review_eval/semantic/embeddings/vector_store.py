"""Qdrant-backed vector store for semantic search.

Uses cloud-hosted Qdrant for production-grade vector storage with cosine similarity search.
Requires QDRANT_URL and QDRANT_API_KEY environment variables.
"""

import hashlib
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PayloadSchemaType, PointStruct, VectorParams

from review_eval.semantic.models import CodeChunk, SearchResult


def _string_to_uuid(s: str) -> str:
    """Convert any string to a valid UUID by hashing it.

    Qdrant Cloud requires point IDs to be either unsigned integers or UUIDs.
    This converts arbitrary string IDs (like SHA256 hashes) to valid UUIDs.
    """
    # Hash the string and take first 16 bytes to create a UUID
    hash_bytes = hashlib.md5(s.encode()).digest()
    return str(uuid.UUID(bytes=hash_bytes))


class VectorStore:
    """Qdrant-backed vector store for code embeddings."""

    def __init__(self, dimension: int = 4096, collection_name: str = "code_chunks") -> None:
        """Initialize the vector store.

        Args:
            dimension: Dimension of embedding vectors.
            collection_name: Name of the Qdrant collection.

        Raises:
            ValueError: If QDRANT_URL or QDRANT_API_KEY environment variables are not set.
        """
        load_dotenv()

        url = os.environ.get("QDRANT_URL")
        api_key = os.environ.get("QDRANT_API_KEY")

        if not url or not api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY must be set in environment")

        self.client = QdrantClient(url=url, api_key=api_key)
        self.collection = collection_name
        self.dimension = dimension
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
            )
            # Create payload index for file_path filtering
            self.client.create_payload_index(
                collection_name=self.collection,
                field_name="file_path",
                field_schema=PayloadSchemaType.KEYWORD,
            )

    def add(
        self,
        chunks: list[CodeChunk],
        embeddings: list[list[float]],
        batch_size: int = 100,
    ) -> None:
        """Add chunks and their embeddings to the store.

        Args:
            chunks: List of code chunks.
            embeddings: List of embedding vectors (same order as chunks).
            batch_size: Number of points to upload per batch (Qdrant has 33MB limit).
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        if not chunks:
            return

        # Process in batches to avoid Qdrant payload size limit (33MB)
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            points = [
                PointStruct(
                    id=_string_to_uuid(chunk.id),
                    vector=embedding,
                    payload={
                        "original_id": chunk.id,  # Store original ID for retrieval
                        "file_path": chunk.file_path,
                        "chunk_type": chunk.chunk_type,
                        "name": chunk.name,
                        "code": chunk.code,
                        "language": chunk.language,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "token_count": chunk.token_count,
                    },
                )
                for chunk, embedding in zip(batch_chunks, batch_embeddings, strict=False)
            ]
            self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> list[SearchResult]:
        """Search for similar chunks using cosine similarity.

        Args:
            query_embedding: Query vector.
            top_k: Maximum number of results to return.
            min_similarity: Minimum similarity threshold.

        Returns:
            List of SearchResult objects sorted by similarity.
        """
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_embedding,
            limit=top_k,
            score_threshold=min_similarity if min_similarity > 0 else None,
        )

        return [
            SearchResult(
                chunk=self._payload_to_chunk(hit.payload),
                similarity=hit.score,
                rank=rank + 1,
            )
            for rank, hit in enumerate(response.points)
        ]

    def _payload_to_chunk(self, payload: dict[str, Any]) -> CodeChunk:
        """Convert Qdrant payload to CodeChunk."""
        return CodeChunk(
            id=payload["original_id"],  # Use original ID, not the UUID
            file_path=payload["file_path"],
            chunk_type=payload["chunk_type"],
            name=payload["name"],
            code=payload["code"],
            language=payload["language"],
            start_line=payload["start_line"],
            end_line=payload["end_line"],
            token_count=payload.get("token_count", 0),
        )

    def save(self, path: Path) -> None:
        """Save the vector store to disk.

        Note: This is a no-op for cloud Qdrant as data is persisted automatically.

        Args:
            path: Directory path (unused for cloud Qdrant).
        """
        pass  # Cloud Qdrant persists automatically

    def load(self, path: Path) -> bool:
        """Load the vector store from disk.

        Note: For cloud Qdrant, this checks if the collection exists and has data.

        Args:
            path: Directory path (unused for cloud Qdrant).

        Returns:
            True if collection exists and has data, False otherwise.
        """
        if not self.client.collection_exists(self.collection):
            return False
        # Only return True if there's actual data to use
        return self.size > 0

    def clear(self) -> None:
        """Clear all stored embeddings and chunks."""
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self._ensure_collection()

    @property
    def size(self) -> int:
        """Return the number of stored chunks."""
        info = self.client.get_collection(self.collection)
        return info.points_count

    def get_chunk_by_id(self, chunk_id: str) -> CodeChunk | None:
        """Get a chunk by its ID.

        Args:
            chunk_id: The chunk ID to look up.

        Returns:
            The CodeChunk if found, None otherwise.
        """
        # Convert the original ID to UUID for lookup
        uuid_id = _string_to_uuid(chunk_id)
        results = self.client.retrieve(
            collection_name=self.collection,
            ids=[uuid_id],
            with_payload=True,
        )
        if not results:
            return None
        hit = results[0]
        return self._payload_to_chunk(hit.payload)

    def remove_by_file(self, file_path: str) -> int:
        """Remove all chunks from a specific file.

        Args:
            file_path: Path of the file to remove chunks for.

        Returns:
            Number of chunks removed.
        """
        count_before = self.size
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(must=[FieldCondition(key="file_path", match=MatchValue(value=file_path))]),
        )
        return count_before - self.size
