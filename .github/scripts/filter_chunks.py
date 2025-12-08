#!/usr/bin/env python3
"""Filter AGENTS.md chunks based on changed files."""
import json
import fnmatch
from pathlib import Path


def matches_glob(file_path: str, patterns: list[str]) -> bool:
    """Check if file matches any of the glob patterns."""
    for pattern in patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


def filter_chunks(chunks_data: dict, changed_files: list[str]) -> dict:
    """Filter chunks to only those relevant to changed files."""
    relevant_chunks = []

    for chunk in chunks_data["chunks"]:
        patterns = chunk.get("applicable_paths", ["**/*"])
        for changed_file in changed_files:
            if matches_glob(changed_file, patterns):
                relevant_chunks.append(chunk)
                break

    return {
        "chunks": relevant_chunks,
        "total_chunks": len(relevant_chunks),
        "filtered_from": chunks_data["total_chunks"]
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", required=True)
    parser.add_argument("--changed-files", required=True)
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    chunks_data = json.loads(Path(args.chunks).read_text())
    changed_files = [f for f in Path(args.changed_files).read_text().strip().split("\n") if f]

    filtered = filter_chunks(chunks_data, changed_files)

    result = json.dumps(filtered, indent=2)
    if args.output:
        Path(args.output).write_text(result)
    else:
        print(result)


if __name__ == "__main__":
    main()
