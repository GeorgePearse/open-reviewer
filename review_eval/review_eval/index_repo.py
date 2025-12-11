#!/usr/bin/env python3
"""CLI script to index a repository into Qdrant for semantic search.

Usage:
    uv run python -m review_eval.index_repo /path/to/repo
    uv run python -m review_eval.index_repo .  # current directory

Environment variables required:
    OPENROUTER_API_KEY - OpenRouter API key for embeddings
    QDRANT_URL - Qdrant Cloud cluster URL
    QDRANT_API_KEY - Qdrant Cloud API key

Optional:
    --force    Force reindex even if data exists
    --dry-run  Just count chunks without embedding
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


def check_env_vars() -> list[str]:
    """Check required environment variables are set."""
    missing = []
    for var in ["OPENROUTER_API_KEY", "QDRANT_URL", "QDRANT_API_KEY"]:
        if not os.environ.get(var):
            missing.append(var)
    return missing


def count_chunks_only(repo_root: Path) -> int:
    """Dry run: just count chunks without embedding."""
    from review_eval.semantic.embeddings.chunker import chunk_repository

    print(f"Scanning {repo_root} for Python files...")
    chunks = chunk_repository(repo_root)
    print(f"\nFound {len(chunks)} code chunks:")

    # Group by type
    by_type: dict[str, int] = {}
    for chunk in chunks:
        by_type[chunk.chunk_type] = by_type.get(chunk.chunk_type, 0) + 1

    for chunk_type, count in sorted(by_type.items()):
        print(f"  - {chunk_type}: {count}")

    return len(chunks)


async def index_repository(repo_root: Path, force: bool = False, max_chunks: int = 10000) -> int:
    """Index a repository into Qdrant."""
    from review_eval.semantic.search import SemanticSearch

    print(f"Indexing {repo_root}...")
    print("  - Chunking Python files")
    print("  - Generating embeddings via OpenRouter (qwen/qwen3-embedding-8b)")
    print("  - Storing vectors in Qdrant (batched uploads)\n")

    search = SemanticSearch(repo_root)

    start = time.time()
    count = await search.index_repository(force_reindex=force, max_chunks=max_chunks, verbose=True)
    elapsed = time.time() - start

    print(f"\nIndexed {count} chunks in {elapsed:.1f}s")
    if elapsed > 0:
        print(f"Average: {count / elapsed:.1f} chunks/sec")

    return count


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Index a repository into Qdrant for semantic code search"
    )
    parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to the repository to index",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reindex even if data exists in Qdrant",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Just count chunks without generating embeddings",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Path to .env file with credentials",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=10000,
        help="Maximum number of chunks to index (default: 10000)",
    )

    args = parser.parse_args()

    # Load environment
    if args.env_file:
        load_dotenv(args.env_file)
    else:
        load_dotenv()

    repo_root = args.repo_path.resolve()
    if not repo_root.is_dir():
        print(f"Error: {repo_root} is not a directory", file=sys.stderr)
        return 1

    # Dry run doesn't need API keys
    if args.dry_run:
        count_chunks_only(repo_root)
        return 0

    # Check environment
    missing = check_env_vars()
    if missing:
        print("Error: Missing required environment variables:", file=sys.stderr)
        for var in missing:
            print(f"  - {var}", file=sys.stderr)
        print("\nSet these in your environment or a .env file.", file=sys.stderr)
        return 1

    # Run indexing
    try:
        asyncio.run(index_repository(repo_root, force=args.force, max_chunks=args.max_chunks))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
