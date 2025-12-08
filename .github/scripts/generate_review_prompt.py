#!/usr/bin/env python3
"""Generate a review prompt for specific AGENTS.md chunks."""

import json
import sys
from pathlib import Path


def load_similar_code_context(similar_code_file: Path | None) -> str:
    """Load similar code context if available."""
    if not similar_code_file or not similar_code_file.exists():
        return ""

    content = similar_code_file.read_text().strip()
    if not content:
        return ""

    return content + "\n\n---\n\n"


def generate_prompt(chunk: dict) -> str:
    """Generate a Claude review prompt for a specific chunk."""
    parts = []

    parts.append(f"## Review Focus: {chunk['section']}")
    parts.append(f"**Source**: `{chunk['file_path']}`")
    parts.append("")

    if chunk.get("rules"):
        parts.append("### Rules to Verify")
        for rule in chunk["rules"]:
            parts.append(f"- {rule}")
        parts.append("")

    if chunk.get("anti_patterns"):
        parts.append("### Anti-Patterns to Flag")
        for pattern in chunk["anti_patterns"]:
            parts.append(f"- {pattern}")
        parts.append("")

    parts.append("### Review Instructions")
    parts.append(f"1. Check files matching: {', '.join(chunk.get('applicable_paths', ['**/*']))}")
    parts.append("2. Verify each rule is followed in the changed code")
    parts.append("3. Flag any anti-patterns found with severity (CRITICAL/HIGH/MEDIUM/LOW)")
    parts.append("4. Post inline comments on specific lines")
    parts.append("5. Use ```suggestion blocks for concrete fixes")
    parts.append(f"6. Prefix comments with [{chunk['id'].upper()}] for traceability")

    return "\n".join(parts)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-ids", required=True, help="Comma-separated chunk IDs")
    parser.add_argument("--chunks", required=True)
    parser.add_argument("--similar-code", type=Path, help="Path to similar code context file")
    args = parser.parse_args()

    chunks_data = json.loads(Path(args.chunks).read_text())
    chunk_ids = [cid.strip() for cid in args.chunk_ids.split(",")]

    # Load similar code context if available
    similar_context = load_similar_code_context(args.similar_code)

    prompts = []
    for chunk_id in chunk_ids:
        chunk = next((c for c in chunks_data["chunks"] if c["id"] == chunk_id), None)
        if chunk:
            prompts.append(generate_prompt(chunk))
        else:
            print(f"Warning: Chunk not found: {chunk_id}", file=sys.stderr)

    # Prepend similar code context to the first prompt
    output = "\n\n---\n\n".join(prompts)
    if similar_context:
        output = similar_context + output

    print(output)


if __name__ == "__main__":
    main()
