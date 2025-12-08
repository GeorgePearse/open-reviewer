#!/usr/bin/env python3
"""Incremental embedding update for changed Python files.

Usage:
    # Update embeddings for files changed between two commits
    uv run python -m review_eval.update_embeddings --before-sha abc123 --after-sha def456

    # Update based on recent changes (for local testing)
    uv run python -m review_eval.update_embeddings --since HEAD~1

    # Dry run to see what would be updated
    uv run python -m review_eval.update_embeddings --since HEAD~1 --dry-run

Environment variables required:
    OPENROUTER_API_KEY - OpenRouter API key for embeddings
    QDRANT_URL - Qdrant Cloud cluster URL
    QDRANT_API_KEY - Qdrant Cloud API key
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class UpdateResult:
    """Result of incremental update operation."""

    files_processed: int
    chunks_removed: int
    chunks_added: int
    files_deleted: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


# Patterns to exclude from indexing (same as chunk_repository)
EXCLUDE_PATTERNS = [
    "test_",
    "_test.py",
    "/tests/",
    "/.venv/",
    "/venv/",
    "/__pycache__/",
    "/node_modules/",
    "/site-packages/",
]


def should_include_file(path: Path) -> bool:
    """Check if a file should be included in indexing."""
    path_str = str(path)
    return not any(pattern in path_str for pattern in EXCLUDE_PATTERNS)


def get_changed_python_files(
    repo_root: Path,
    before_sha: str | None = None,
    after_sha: str | None = None,
    since: str | None = None,
) -> tuple[list[Path], list[Path]]:
    """Get changed and deleted Python files from git.

    Args:
        repo_root: Repository root.
        before_sha: SHA before changes (for CI: github.event.before).
        after_sha: SHA after changes (for CI: github.sha).
        since: Alternative: Git ref for comparison (e.g., HEAD~1).

    Returns:
        Tuple of (changed_files, deleted_files).
    """
    # Handle initial push where before_sha is all zeros
    if before_sha and before_sha == "0000000000000000000000000000000000000000":
        # Initial push - treat as if comparing to HEAD~1 or empty
        before_sha = None
        since = "HEAD~1"

    if before_sha and after_sha:
        cmd = ["git", "diff", "--name-status", before_sha, after_sha, "--", "*.py"]
    elif since:
        cmd = ["git", "diff", "--name-status", since, "HEAD", "--", "*.py"]
    else:
        raise ValueError("Must provide either (before_sha, after_sha) or since")

    try:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        # If git diff fails (e.g., invalid ref), return empty
        print(f"Warning: git diff failed: {e.stderr}", file=sys.stderr)
        return [], []

    changed_files: list[Path] = []
    deleted_files: list[Path] = []

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]

        # Handle renames (R100 old_path new_path)
        if status.startswith("R"):
            old_path = repo_root / parts[1]
            new_path = repo_root / parts[2]
            # Treat rename as delete old + add new
            if should_include_file(old_path):
                deleted_files.append(old_path)
            if should_include_file(new_path) and new_path.suffix == ".py":
                changed_files.append(new_path)
        elif status.startswith("D"):
            file_path = repo_root / parts[1]
            if should_include_file(file_path):
                deleted_files.append(file_path)
        else:
            # A (added), M (modified), C (copied)
            file_path = repo_root / parts[-1]
            if file_path.suffix == ".py" and should_include_file(file_path):
                changed_files.append(file_path)

    return changed_files, deleted_files


async def update_changed_files(
    repo_root: Path,
    changed_files: list[Path],
    deleted_files: list[Path],
    verbose: bool = False,
) -> UpdateResult:
    """Update embeddings for changed files only.

    Args:
        repo_root: Repository root directory.
        changed_files: List of modified/added Python files.
        deleted_files: List of deleted Python files.
        verbose: Print progress.

    Returns:
        UpdateResult with statistics.
    """
    from review_eval.semantic.embeddings.chunker import chunk_python_file
    from review_eval.semantic.embeddings.client import EmbeddingClient
    from review_eval.semantic.embeddings.vector_store import VectorStore

    start_time = time.time()

    client = EmbeddingClient()
    store = VectorStore(dimension=client.dimension)

    chunks_removed = 0
    chunks_added = 0

    # Step 1: Remove embeddings for deleted files
    for file_path in deleted_files:
        rel_path = str(file_path.relative_to(repo_root))
        removed = store.remove_by_file(rel_path)
        chunks_removed += removed
        if verbose:
            print(f"  Removed {removed} chunks for deleted file: {rel_path}")

    # Step 2: Remove old embeddings for modified/added files
    for file_path in changed_files:
        rel_path = str(file_path.relative_to(repo_root))
        removed = store.remove_by_file(rel_path)
        chunks_removed += removed
        if verbose and removed > 0:
            print(f"  Removed {removed} old chunks for: {rel_path}")

    # Step 3: Chunk modified/added files
    all_chunks = []
    for file_path in changed_files:
        if file_path.exists():
            chunks = chunk_python_file(file_path, repo_root)
            all_chunks.extend(chunks)
            if verbose:
                print(f"  Chunked {len(chunks)} items from: {file_path.relative_to(repo_root)}")

    # Step 4: Generate embeddings and add to store
    if all_chunks:
        if verbose:
            print(f"\nGenerating embeddings for {len(all_chunks)} chunks...")
        results = await client.embed_chunks(all_chunks)
        store.add(
            chunks=[r.chunk for r in results],
            embeddings=[r.embedding for r in results],
        )
        chunks_added = len(results)
        if verbose:
            print(f"  Added {chunks_added} new embeddings to Qdrant")

    elapsed = time.time() - start_time

    return UpdateResult(
        files_processed=len(changed_files) + len(deleted_files),
        chunks_removed=chunks_removed,
        chunks_added=chunks_added,
        files_deleted=[str(f.relative_to(repo_root)) for f in deleted_files],
        files_modified=[str(f.relative_to(repo_root)) for f in changed_files if f.exists()],
        elapsed_seconds=elapsed,
    )


def check_env_vars() -> list[str]:
    """Check required environment variables are set."""
    missing = []
    for var in ["OPENROUTER_API_KEY", "QDRANT_URL", "QDRANT_API_KEY"]:
        if not os.environ.get(var):
            missing.append(var)
    return missing


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Incrementally update embeddings for changed Python files")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory (default: current directory)",
    )
    parser.add_argument(
        "--since",
        type=str,
        help="Git ref to compare against (e.g., HEAD~1, origin/main)",
    )
    parser.add_argument(
        "--before-sha",
        type=str,
        help="SHA before changes (for CI: github.event.before)",
    )
    parser.add_argument(
        "--after-sha",
        type=str,
        help="SHA after changes (for CI: github.sha)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed progress",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Path to .env file with credentials",
    )

    args = parser.parse_args()

    # Load environment
    if args.env_file:
        load_dotenv(args.env_file)
    else:
        load_dotenv()

    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        print(f"Error: {repo_root} is not a directory", file=sys.stderr)
        return 1

    # Validate args
    if not args.since and not (args.before_sha and args.after_sha):
        # Default to comparing against HEAD~1
        args.since = "HEAD~1"

    # Get changed files
    try:
        changed_files, deleted_files = get_changed_python_files(
            repo_root,
            before_sha=args.before_sha,
            after_sha=args.after_sha,
            since=args.since,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if not changed_files and not deleted_files:
        print("No Python files changed, nothing to update.")
        return 0

    print(f"Found {len(changed_files)} modified/added and {len(deleted_files)} deleted Python files")

    if args.dry_run:
        print("\nDry run - would update:")
        for f in changed_files:
            print(f"  M {f.relative_to(repo_root)}")
        for f in deleted_files:
            print(f"  D {f.relative_to(repo_root)}")
        return 0

    # Check environment
    missing = check_env_vars()
    if missing:
        print("Error: Missing required environment variables:", file=sys.stderr)
        for var in missing:
            print(f"  - {var}", file=sys.stderr)
        return 1

    # Run update
    try:
        result = asyncio.run(
            update_changed_files(
                repo_root,
                changed_files,
                deleted_files,
                verbose=args.verbose,
            )
        )
    except Exception as e:
        print(f"Error updating embeddings: {e}", file=sys.stderr)
        return 1

    print("\nUpdate complete:")
    print(f"  Files processed: {result.files_processed}")
    print(f"  Chunks removed: {result.chunks_removed}")
    print(f"  Chunks added: {result.chunks_added}")
    print(f"  Time: {result.elapsed_seconds:.1f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
