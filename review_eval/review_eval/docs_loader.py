"""Documentation loader for injecting CLAUDE.md/AGENTS.md and /docs into review prompts."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DocumentationFile:
    """Represents a documentation file with metadata."""

    path: Path
    scope: str  # "global", directory name, or doc category
    priority: int  # 0 = global, higher = more specific
    content: str
    token_estimate: int
    doc_type: str = "agents"  # "agents" for CLAUDE/AGENTS.md, "reference" for /docs
    keywords: list[str] = field(default_factory=list)  # Keywords for matching


# Mapping of /docs categories to relevant code paths
DOCS_PATH_MAPPINGS: dict[str, list[str]] = {
    "explanations/metrics": ["backend/metrics", "dbt/models"],
    "explanations/deep-learning": ["machine_learning/"],
    "explanations/evaluation-system": ["machine_learning/packages/eval"],
    "explanations/clickhouse": ["backend/", "dbt/"],
    "guides/adding-a-new-handler": ["backend/handlers", "lib/python/pipelines"],
    "guides/evaluate": ["machine_learning/packages/eval"],
    "guides/offline-inference": ["machine_learning/", "backend/inference"],
    "references/linting": ["**/*"],  # Global relevance
    "references/testing": ["**/*"],  # Global relevance
    "references/python-apps": ["backend/", "lib/python/"],
    "references/ml-packages": ["machine_learning/packages/"],
    "references/hooks": ["**/*"],  # Global relevance
}


def _extract_keywords(content: str, path: Path) -> list[str]:
    """Extract keywords from doc content and path for matching."""
    keywords: list[str] = []

    # Extract from path
    for part in path.parts:
        if part not in ("docs", "README.md", "index.md"):
            keywords.append(part.lower().replace("-", "_").replace(".md", ""))

    # Extract common technical terms from content
    tech_terms = [
        "postgres",
        "clickhouse",
        "dbt",
        "graphql",
        "api",
        "handler",
        "pipeline",
        "inference",
        "training",
        "evaluation",
        "metrics",
        "model",
        "detection",
        "classification",
        "segmentation",
        "tracker",
        "gcs",
        "bucket",
        "terraform",
    ]
    content_lower = content.lower()
    for term in tech_terms:
        if term in content_lower:
            keywords.append(term)

    return list(set(keywords))


def discover_docs(repo_root: Path, include_docs_dir: bool = True) -> list[DocumentationFile]:
    """Find all CLAUDE.md, AGENTS.md, and /docs markdown files.

    Args:
        repo_root: Root path of the repository.
        include_docs_dir: Whether to include files from /docs directory.

    Returns:
        List of DocumentationFile objects sorted by priority.
    """
    docs: list[DocumentationFile] = []

    # Root CLAUDE.md (priority 0 - always included)
    root_claude = repo_root / "CLAUDE.md"
    if root_claude.exists():
        content = root_claude.read_text()
        docs.append(
            DocumentationFile(
                path=root_claude,
                scope="global",
                priority=0,
                content=content,
                token_estimate=len(content) // 4,
                doc_type="agents",
                keywords=["global", "repository", "guidelines"],
            )
        )

    # Nested AGENTS.md files
    for agents_file in sorted(repo_root.rglob("AGENTS.md")):
        # Skip root AGENTS.md (same content as CLAUDE.md in this repo)
        if agents_file.parent == repo_root:
            continue

        relative_path = agents_file.relative_to(repo_root)
        depth = len(relative_path.parts) - 1
        content = agents_file.read_text()

        docs.append(
            DocumentationFile(
                path=agents_file,
                scope=str(relative_path.parent),
                priority=depth,
                content=content,
                token_estimate=len(content) // 4,
                doc_type="agents",
                keywords=_extract_keywords(content, relative_path),
            )
        )

    # Include /docs directory markdown files
    if include_docs_dir:
        docs_dir = repo_root / "docs"
        if docs_dir.exists():
            for doc_file in sorted(docs_dir.rglob("*.md")):
                # Skip index/README files (usually just navigation)
                if doc_file.name in ("index.md", "README.md", "SUMMARY.md"):
                    continue

                relative_path = doc_file.relative_to(repo_root)
                content = doc_file.read_text()

                # Determine scope from path (e.g., "docs/explanations/metrics")
                scope = str(relative_path.parent)

                docs.append(
                    DocumentationFile(
                        path=doc_file,
                        scope=scope,
                        priority=10,  # Lower priority than AGENTS.md
                        content=content,
                        token_estimate=len(content) // 4,
                        doc_type="reference",
                        keywords=_extract_keywords(content, relative_path),
                    )
                )

    return docs


def _path_matches_pattern(file_path: str, pattern: str) -> bool:
    """Check if a file path matches a pattern (supports ** glob)."""
    if pattern == "**/*":
        return True

    file_path_lower = file_path.lower()
    pattern_lower = pattern.lower().rstrip("/")

    return file_path_lower.startswith(pattern_lower)


def select_docs_for_path(
    file_path: str,
    all_docs: list[DocumentationFile],
    repo_root: Path | None = None,
    include_keyword_matches: bool = True,
) -> list[DocumentationFile]:
    """Select documentation relevant to a file path.

    Includes:
    1. Global docs (always)
    2. AGENTS.md files in ancestor directories
    3. /docs files that match by keyword or path mapping

    Args:
        file_path: Path to the file being reviewed (relative to repo root).
        all_docs: List of all discovered documentation files.
        repo_root: Optional repo root for resolving paths.
        include_keyword_matches: Whether to include /docs matched by keyword.

    Returns:
        List of relevant DocumentationFile objects sorted by priority.
    """
    relevant: list[DocumentationFile] = []
    file_path_obj = Path(file_path)

    # Extract keywords from file path for matching
    path_keywords = set()
    for part in file_path_obj.parts:
        path_keywords.add(part.lower().replace("-", "_"))
        path_keywords.add(part.lower())

    for doc in all_docs:
        # Always include global docs
        if doc.scope == "global":
            relevant.append(doc)
            continue

        # For AGENTS.md files, check if scope is ancestor of file path
        if doc.doc_type == "agents":
            scope_path = Path(doc.scope)
            try:
                file_path_obj.relative_to(scope_path)
                relevant.append(doc)
            except ValueError:
                pass
            continue

        # For /docs reference files, use keyword and path mapping
        if doc.doc_type == "reference" and include_keyword_matches:
            # Check path mappings
            for doc_pattern, code_patterns in DOCS_PATH_MAPPINGS.items():
                if doc_pattern in doc.scope:
                    for code_pattern in code_patterns:
                        if _path_matches_pattern(file_path, code_pattern):
                            relevant.append(doc)
                            break
                    break

            # Check keyword overlap (if not already added)
            if doc not in relevant and doc.keywords:
                keyword_overlap = path_keywords.intersection(set(doc.keywords))
                if len(keyword_overlap) >= 1:
                    relevant.append(doc)

    # Sort: global first, then agents by priority, then references
    def sort_key(d: DocumentationFile) -> tuple[int, int, str]:
        type_order = 0 if d.doc_type == "agents" else 1
        return (type_order, d.priority, d.scope)

    return sorted(relevant, key=sort_key)


def build_docs_prompt(
    docs: list[DocumentationFile],
    max_tokens: int = 25000,
) -> str:
    """Build a prompt section from documentation files.

    Respects token budget by including docs in priority order until budget exhausted.

    Args:
        docs: List of documentation files to include.
        max_tokens: Maximum tokens to include (approximate).

    Returns:
        Formatted prompt string with documentation.
    """
    if not docs:
        return ""

    parts: list[str] = ["# Repository Documentation\n"]
    remaining = max_tokens
    included_count = 0
    truncated_docs: list[str] = []

    # Separate agents docs from reference docs
    agents_docs = [d for d in docs if d.doc_type == "agents"]
    reference_docs = [d for d in docs if d.doc_type == "reference"]

    # Include agents docs first (higher priority)
    if agents_docs:
        parts.append("## Coding Guidelines (CLAUDE.md / AGENTS.md)\n")
        for doc in agents_docs:
            if doc.token_estimate <= remaining:
                scope_title = doc.scope.replace("/", " > ").title()
                if doc.scope == "global":
                    scope_title = "Global Repository Rules"
                parts.append(f"### {scope_title}\n\n{doc.content}")
                remaining -= doc.token_estimate
                included_count += 1
            else:
                truncated_docs.append(f"{doc.scope} (AGENTS)")

    # Include reference docs
    if reference_docs and remaining > 1000:
        parts.append("\n## Reference Documentation (/docs)\n")
        for doc in reference_docs:
            if doc.token_estimate <= remaining:
                # Use filename as title
                title = doc.path.stem.replace("-", " ").replace("_", " ").title()
                category = doc.path.parent.name.title()
                parts.append(f"### {category}: {title}\n\n{doc.content}")
                remaining -= doc.token_estimate
                included_count += 1
            else:
                truncated_docs.append(f"{doc.path.stem}")

    # Add truncation notice if needed
    if truncated_docs:
        truncated_list = ", ".join(truncated_docs[:5])
        ellipsis = "..." if len(truncated_docs) > 5 else ""
        parts.append(f"\n_Note: {len(truncated_docs)} additional docs truncated: {truncated_list}{ellipsis}_")

    return "\n\n---\n\n".join(parts)


def get_doc_coverage_report(
    repo_root: Path,
    code_paths: list[str],
) -> dict:
    """Generate a report on documentation coverage for given code paths.

    Useful for identifying areas that may need better documentation.

    Args:
        repo_root: Root path of the repository.
        code_paths: List of code file paths to check coverage for.

    Returns:
        Dict with coverage statistics and gaps.
    """
    all_docs = discover_docs(repo_root)

    covered_paths: list[str] = []
    uncovered_paths: list[str] = []

    for path in code_paths:
        relevant = select_docs_for_path(path, all_docs, include_keyword_matches=True)
        # Check if we have more than just global docs
        non_global = [d for d in relevant if d.scope != "global"]
        if non_global:
            covered_paths.append(path)
        else:
            uncovered_paths.append(path)

    return {
        "total_paths": len(code_paths),
        "covered_count": len(covered_paths),
        "uncovered_count": len(uncovered_paths),
        "coverage_percent": len(covered_paths) / len(code_paths) * 100 if code_paths else 0,
        "uncovered_paths": uncovered_paths,
        "total_docs": len(all_docs),
        "agents_docs": len([d for d in all_docs if d.doc_type == "agents"]),
        "reference_docs": len([d for d in all_docs if d.doc_type == "reference"]),
    }
