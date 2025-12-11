#!/usr/bin/env python3
"""Fetch similar code from Qdrant for PR review context.

This script reads changed files from a PR and finds similar code patterns
in the codebase using semantic search. The output is formatted as context
for Claude to use during code review.

Usage:
    python fetch_similar_code.py \
        --changed-files changed_files.txt \
        --repo-root /path/to/repo \
        --output similar_code.md

Environment variables required:
    OPENROUTER_API_KEY - OpenRouter API key for embeddings
    QDRANT_URL - Qdrant Cloud cluster URL
    QDRANT_API_KEY - Qdrant Cloud API key
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any


def check_env_vars() -> list[str]:
    """Check required environment variables are set."""
    missing = []
    for var in ["OPENROUTER_API_KEY", "QDRANT_URL", "QDRANT_API_KEY"]:
        if not os.environ.get(var):
            missing.append(var)
    return missing


async def find_similar_for_file(
    file_path: Path,
    repo_root: Path,
    client: Any,  # EmbeddingClient from review_eval
    store: Any,  # VectorStore from review_eval
    top_k: int = 3,
    min_similarity: float = 0.5,
) -> list[dict[str, Any]]:
    """Find similar code for a single file."""
    # Read the file content
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    # Skip very small files
    if len(content) < 50:
        return []

    # Embed the file content
    try:
        query_embedding = await client.embed_text(content[:6000])  # Limit to ~1500 tokens
    except Exception as e:
        print(f"Warning: Failed to embed {file_path}: {e}", file=sys.stderr)
        return []

    # Search for similar code
    results = store.search(
        query_embedding,
        top_k=top_k + 5,  # Get extra to filter out same file
        min_similarity=min_similarity,
    )

    # Filter out results from the same file and exclude venv/vendor paths
    rel_path = str(file_path.relative_to(repo_root))
    exclude_patterns = (".venv/", "/venv/", "site-packages/", "node_modules/", "__pycache__/")
    filtered: list[dict[str, Any]] = []
    for r in results:
        # Skip same file and excluded paths
        if r.chunk.file_path == rel_path:
            continue
        if any(pattern in r.chunk.file_path for pattern in exclude_patterns):
            continue
        filtered.append(
            {
                "file": r.chunk.file_path,
                "name": r.chunk.name,
                "type": r.chunk.chunk_type,
                "similarity": round(r.similarity, 3),
                "lines": f"{r.chunk.start_line}-{r.chunk.end_line}",
                "code_preview": r.chunk.code[:200] + "..." if len(r.chunk.code) > 200 else r.chunk.code,
            }
        )
        if len(filtered) >= top_k:
            break

    return filtered


async def main_async(
    changed_files: list[Path],
    repo_root: Path,
    top_k: int = 3,
    min_similarity: float = 0.5,
) -> dict[str, list[dict[str, Any]]]:
    """Find similar code for all changed files."""
    # Import here to avoid issues when env vars not set
    sys.path.insert(0, str(repo_root / "review_eval"))
    from review_eval.semantic.embeddings.client import EmbeddingClient  # pyright: ignore[reportMissingImports]
    from review_eval.semantic.embeddings.vector_store import VectorStore  # pyright: ignore[reportMissingImports]

    client = EmbeddingClient()
    store = VectorStore(dimension=client.dimension)

    # Check if index exists
    if store.size == 0:
        print("Warning: Qdrant index is empty. Run index_repo.py first.", file=sys.stderr)
        return {}

    results: dict[str, list[dict[str, Any]]] = {}
    for file_path in changed_files:
        if not file_path.exists():
            continue
        if file_path.suffix not in [".py", ".ts", ".tsx", ".rs", ".go", ".java"]:
            continue  # Only supported languages

        similar = await find_similar_for_file(file_path, repo_root, client, store, top_k, min_similarity)
        if similar:
            rel_path = str(file_path.relative_to(repo_root))
            results[rel_path] = similar

    return results


def format_as_markdown(results: dict[str, list[dict[str, Any]]]) -> str:
    """Format results as markdown for Claude context."""
    if not results:
        return ""

    lines = ["## Similar Code Patterns in Codebase", ""]
    lines.append("The following existing code patterns are similar to files in this PR.")
    lines.append("Consider these when reviewing for consistency and potential reuse.")
    lines.append("")

    for changed_file, similar_items in results.items():
        lines.append(f"### Similar to `{changed_file}`")
        lines.append("")
        for item in similar_items:
            lines.append(f"- **{item['file']}:{item['lines']}** - `{item['name']}` ({item['type']}, {item['similarity']:.0%} similar)")
        lines.append("")

    return "\n".join(lines)


def format_as_json(results: dict[str, list[dict[str, Any]]]) -> str:
    """Format results as JSON."""
    return json.dumps(results, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch similar code from Qdrant for PR review context")
    parser.add_argument(
        "--changed-files",
        type=Path,
        required=True,
        help="File containing list of changed files (one per line)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of similar items per file",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.5,
        help="Minimum similarity threshold (0-1)",
    )

    args = parser.parse_args()

    # Check environment
    missing = check_env_vars()
    if missing:
        print(f"Warning: Missing env vars: {', '.join(missing)}", file=sys.stderr)
        print("Semantic search will be skipped.", file=sys.stderr)
        # Output empty result instead of failing
        output = "" if args.format == "markdown" else "{}"
        if args.output:
            args.output.write_text(output)
        else:
            print(output)
        return 0

    # Read changed files
    if not args.changed_files.exists():
        print(f"Error: {args.changed_files} not found", file=sys.stderr)
        return 1

    changed_files = [args.repo_root / line.strip() for line in args.changed_files.read_text().strip().split("\n") if line.strip()]

    if not changed_files:
        print("No changed files to analyze", file=sys.stderr)
        output = "" if args.format == "markdown" else "{}"
        if args.output:
            args.output.write_text(output)
        else:
            print(output)
        return 0

    # Run async search
    try:
        results = asyncio.run(
            main_async(
                changed_files,
                args.repo_root,
                top_k=args.top_k,
                min_similarity=args.min_similarity,
            )
        )
    except Exception as e:
        print(f"Warning: Semantic search failed: {e}", file=sys.stderr)
        results = {}

    # Format output
    if args.format == "markdown":
        output = format_as_markdown(results)
    else:
        output = format_as_json(results)

    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"Wrote similar code context to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
