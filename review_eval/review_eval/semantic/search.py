"""Unified semantic search orchestration.

Combines chunking, embedding, and vector search into a high-level API
for finding semantically similar code.
"""

import asyncio
from pathlib import Path

from review_eval.semantic.embeddings.chunker import chunk_repository
from review_eval.semantic.embeddings.client import EmbeddingClient, MockEmbeddingClient
from review_eval.semantic.embeddings.vector_store import VectorStore
from review_eval.semantic.models import CodeChunk, SemanticSearchResults


class SemanticSearch:
    """High-level semantic search for code repositories."""

    def __init__(
        self,
        repo_root: Path,
        cache_dir: Path | None = None,
        use_mock: bool = False,
    ) -> None:
        """Initialize semantic search.

        Args:
            repo_root: Root directory of the repository.
            cache_dir: Directory for caching embeddings. Defaults to repo_root/.semantic_cache.
            use_mock: Use mock embeddings for testing.
        """
        self.repo_root = Path(repo_root)
        self.cache_dir = cache_dir or (self.repo_root / ".semantic_cache")

        if use_mock:
            self._client: EmbeddingClient = MockEmbeddingClient()
        else:
            self._client = EmbeddingClient()

        self._store = VectorStore(dimension=self._client.dimension)
        self._indexed = False

    async def index_repository(
        self,
        force_reindex: bool = False,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_chunks: int = 10000,
        verbose: bool = False,
    ) -> int:
        """Index the repository for semantic search.

        Args:
            force_reindex: If True, reindex even if cache exists.
            include_patterns: Glob patterns for files to include.
            exclude_patterns: Glob patterns for files to exclude.
            max_chunks: Maximum number of chunks to index.
            verbose: Print progress updates.

        Returns:
            Number of chunks indexed.
        """
        # Try to load from cache
        if not force_reindex and self._store.load(self.cache_dir):
            self._indexed = True
            return self._store.size

        # Chunk the repository
        if verbose:
            print(f"Chunking repository: {self.repo_root}")
        chunks = chunk_repository(
            self.repo_root,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            max_chunks=max_chunks,
        )

        if not chunks:
            return 0

        if verbose:
            print(f"Found {len(chunks)} chunks, generating embeddings...")

        # Generate embeddings
        results = await self._client.embed_chunks(chunks)

        if verbose:
            print(f"Uploading {len(results)} vectors to Qdrant...")

        # Add to store
        self._store.clear()
        self._store.add(
            chunks=[r.chunk for r in results],
            embeddings=[r.embedding for r in results],
        )

        # Save cache
        self._store.save(self.cache_dir)
        self._indexed = True

        if verbose:
            print(f"Indexed {self._store.size} chunks")

        return self._store.size

    async def find_similar(
        self,
        query: str,
        top_k: int = 5,
        max_tokens: int = 8000,
        min_similarity: float = 0.3,
    ) -> SemanticSearchResults:
        """Find code similar to a query.

        Args:
            query: Query code or natural language description.
            top_k: Maximum number of results.
            max_tokens: Maximum tokens for returned code.
            min_similarity: Minimum similarity threshold.

        Returns:
            SemanticSearchResults with matching code chunks.
        """
        if not self._indexed:
            await self.index_repository()

        # Embed the query
        query_embedding = await self._client.embed_text(query)

        # Search
        results = self._store.search(
            query_embedding,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        return SemanticSearchResults(query=query, results=results)

    async def find_similar_to_chunk(
        self,
        chunk: CodeChunk,
        top_k: int = 5,
        min_similarity: float = 0.3,
        exclude_same_file: bool = True,
    ) -> SemanticSearchResults:
        """Find code similar to a specific chunk.

        Args:
            chunk: Code chunk to find similar code for.
            top_k: Maximum number of results.
            min_similarity: Minimum similarity threshold.
            exclude_same_file: Exclude results from the same file.

        Returns:
            SemanticSearchResults with matching code chunks.
        """
        results = await self.find_similar(
            chunk.code,
            top_k=top_k + 5,  # Get extra in case we filter
            min_similarity=min_similarity,
        )

        if exclude_same_file:
            results.results = [r for r in results.results if r.chunk.file_path != chunk.file_path][:top_k]

        return results

    def index_repository_sync(
        self,
        force_reindex: bool = False,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> int:
        """Synchronous wrapper for index_repository."""
        return asyncio.run(
            self.index_repository(
                force_reindex=force_reindex,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            )
        )

    def find_similar_sync(
        self,
        query: str,
        top_k: int = 5,
        max_tokens: int = 8000,
        min_similarity: float = 0.3,
    ) -> SemanticSearchResults:
        """Synchronous wrapper for find_similar."""
        return asyncio.run(
            self.find_similar(
                query=query,
                top_k=top_k,
                max_tokens=max_tokens,
                min_similarity=min_similarity,
            )
        )


async def find_similar_code_for_review(
    code: str,
    repo_root: Path,
    file_path: str,
    top_k: int = 5,
    max_tokens: int = 8000,
    use_mock: bool = False,
) -> str:
    """Find similar code patterns for a code review.

    This is a convenience function for the SemanticEvaluator.

    Args:
        code: Code being reviewed.
        repo_root: Root directory of the repository.
        file_path: Path of the file being reviewed.
        top_k: Maximum number of similar code sections to return.
        max_tokens: Maximum tokens for the output.
        use_mock: Use mock embeddings for testing.

    Returns:
        Formatted markdown string with similar code sections.
    """
    search = SemanticSearch(repo_root, use_mock=use_mock)

    # Ensure repository is indexed
    await search.index_repository()

    # Find similar code
    results = await search.find_similar(
        code,
        top_k=top_k,
        min_similarity=0.4,
    )

    # Filter out results from the same file
    results.results = [r for r in results.results if r.chunk.file_path != file_path]

    return results.format(max_tokens=max_tokens)


def find_similar_code_for_review_sync(
    code: str,
    repo_root: Path,
    file_path: str,
    top_k: int = 5,
    max_tokens: int = 8000,
    use_mock: bool = False,
) -> str:
    """Synchronous wrapper for find_similar_code_for_review."""
    return asyncio.run(
        find_similar_code_for_review(
            code=code,
            repo_root=repo_root,
            file_path=file_path,
            top_k=top_k,
            max_tokens=max_tokens,
            use_mock=use_mock,
        )
    )
