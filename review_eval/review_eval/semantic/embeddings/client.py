"""Embedding client for generating vector embeddings via OpenRouter.

Uses OpenAI's text-embedding-3-small model through OpenRouter for cost efficiency.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import ClassVar

import httpx

from review_eval.semantic.models import CodeChunk


@dataclass
class EmbeddingResult:
    """Result of embedding a code chunk."""

    chunk: CodeChunk
    embedding: list[float]


class EmbeddingClient:
    """Client for generating embeddings via OpenRouter."""

    # Qwen embedding model through OpenRouter
    # Works reliably; 4096 dimensions
    DEFAULT_MODEL = "qwen/qwen3-embedding-8b"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    # Model dimension mapping
    MODEL_DIMENSIONS: ClassVar[dict[str, int]] = {
        "qwen/qwen3-embedding-8b": 4096,
        "openai/text-embedding-3-small": 1536,
        "openai/text-embedding-3-large": 3072,
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        batch_size: int = 100,
    ) -> None:
        """Initialize the embedding client.

        Args:
            api_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.
            model: Model to use for embeddings.
            batch_size: Number of texts to embed per API call.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = model or self.DEFAULT_MODEL
        self.batch_size = batch_size
        self._dimension: int | None = None

    @property
    def dimension(self) -> int:
        """Get the embedding dimension for the current model."""
        if self._dimension is None:
            self._dimension = self.MODEL_DIMENSIONS.get(self.model, 4096)
        return self._dimension

    async def embed_chunks(
        self,
        chunks: list[CodeChunk],
    ) -> list[EmbeddingResult]:
        """Generate embeddings for a list of code chunks.

        Args:
            chunks: List of code chunks to embed.

        Returns:
            List of EmbeddingResult objects with chunks and their embeddings.
        """
        if not chunks:
            return []

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        results: list[EmbeddingResult] = []

        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i : i + self.batch_size]
            texts = [self._prepare_text(chunk) for chunk in batch]

            embeddings = await self._embed_batch(texts)

            for chunk, embedding in zip(batch, embeddings, strict=False):
                results.append(EmbeddingResult(chunk=chunk, embedding=embedding))

        return results

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        embeddings = await self._embed_batch([text])
        return embeddings[0]

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts via OpenRouter API.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.OPENROUTER_BASE_URL}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
            )

            if response.status_code != 200:
                raise RuntimeError(f"Embedding API error: {response.status_code} {response.text}")

            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]
            return embeddings

    def _prepare_text(self, chunk: CodeChunk) -> str:
        """Prepare a code chunk for embedding.

        Formats the chunk with metadata to improve semantic matching.

        Args:
            chunk: Code chunk to prepare.

        Returns:
            Formatted text for embedding.
        """
        # Include metadata for better semantic matching
        prefix = f"# {chunk.chunk_type}: {chunk.name}\n# File: {chunk.file_path}\n\n"
        return prefix + chunk.code[:6000]  # Limit to ~1500 tokens

    def embed_chunks_sync(self, chunks: list[CodeChunk]) -> list[EmbeddingResult]:
        """Synchronous wrapper for embed_chunks.

        Args:
            chunks: List of code chunks to embed.

        Returns:
            List of EmbeddingResult objects.
        """
        return asyncio.run(self.embed_chunks(chunks))

    def embed_text_sync(self, text: str) -> list[float]:
        """Synchronous wrapper for embed_text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        return asyncio.run(self.embed_text(text))


class MockEmbeddingClient(EmbeddingClient):
    """Mock embedding client for testing without API calls."""

    def __init__(self, dimension: int = 4096) -> None:
        """Initialize mock client.

        Args:
            dimension: Dimension of fake embeddings to generate.
        """
        super().__init__(api_key="mock")
        self._dimension = dimension

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic fake embeddings based on text content.

        Args:
            texts: List of texts to embed.

        Returns:
            List of fake embedding vectors.
        """
        embeddings: list[list[float]] = []
        for text in texts:
            # Generate deterministic embedding based on text hash
            import hashlib

            text_hash = hashlib.sha256(text.encode()).digest()
            # Create a normalized vector from the hash
            embedding = [(byte / 255.0 - 0.5) * 2 for byte in (text_hash * (self.dimension // 32 + 1))[: self.dimension]]
            # Normalize to unit length
            norm = sum(x * x for x in embedding) ** 0.5
            embedding = [x / norm for x in embedding]
            embeddings.append(embedding)
        return embeddings
