"""Semantic-aware evaluator combining documentation, AST, repo map, and embeddings."""

import asyncio
from pathlib import Path

from review_eval.docs_loader import (
    build_docs_prompt,
    discover_docs,
    select_docs_for_path,
)
from review_eval.models import ModelConfig
from review_eval.multi_model_evaluator import MultiModelEvaluator
from review_eval.semantic.ast_parser import ASTParser
from review_eval.semantic.repo_map import RepoMapGenerator
from review_eval.semantic.search import SemanticSearch


class SemanticEvaluator(MultiModelEvaluator):
    """Evaluator with full semantic context for code review.

    Combines four types of context:
    1. Documentation (CLAUDE.md, AGENTS.md) - Repository guidelines
    2. AST Context - Function signatures, imports, call sites
    3. Repository Map - Aider-style codebase overview
    4. Similar Code - Embedding-based semantic search

    Token Budget (default 30K total):
    - Documentation: 15K
    - AST Context: 3K
    - Repository Map: 2K
    - Similar Code: 8K
    - Review Instructions: 2K
    """

    def __init__(
        self,
        repo_root: Path,
        file_path: str,
        code: str,
        models: list[ModelConfig] | None = None,
        extra_instructions: str = "",
        api_key: str | None = None,
        enable_ast: bool = True,
        enable_repo_map: bool = True,
        enable_embeddings: bool = False,  # Disabled by default (requires indexing)
        use_mock_embeddings: bool = False,
        max_doc_tokens: int = 15000,
        max_ast_tokens: int = 3000,
        max_map_tokens: int = 2000,
        max_embedding_tokens: int = 8000,
    ) -> None:
        """Initialize the semantic evaluator.

        Args:
            repo_root: Path to the repository root.
            file_path: Path to the file being reviewed (relative to repo root).
            code: The code being reviewed.
            models: List of models to use (defaults to DEFAULT_MODELS).
            extra_instructions: Additional review instructions to append.
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var).
            enable_ast: Include AST context (function signatures, imports).
            enable_repo_map: Include repository map context.
            enable_embeddings: Include similar code via embeddings.
            use_mock_embeddings: Use mock embeddings for testing.
            max_doc_tokens: Maximum tokens for documentation.
            max_ast_tokens: Maximum tokens for AST context.
            max_map_tokens: Maximum tokens for repository map.
            max_embedding_tokens: Maximum tokens for similar code.
        """
        self.repo_root = Path(repo_root)
        self.file_path = file_path
        self.code = code

        # Build the prompt with all enabled context types
        prompt = self._build_prompt(
            enable_ast=enable_ast,
            enable_repo_map=enable_repo_map,
            enable_embeddings=enable_embeddings,
            use_mock_embeddings=use_mock_embeddings,
            extra_instructions=extra_instructions,
            max_doc_tokens=max_doc_tokens,
            max_ast_tokens=max_ast_tokens,
            max_map_tokens=max_map_tokens,
            max_embedding_tokens=max_embedding_tokens,
        )

        super().__init__(prompt, models, api_key)

    def _build_prompt(
        self,
        enable_ast: bool,
        enable_repo_map: bool,
        enable_embeddings: bool,
        use_mock_embeddings: bool,
        extra_instructions: str,
        max_doc_tokens: int,
        max_ast_tokens: int,
        max_map_tokens: int,
        max_embedding_tokens: int,
    ) -> str:
        """Build the complete prompt with all enabled context types."""
        sections: list[str] = []

        # 1. Documentation context
        all_docs = discover_docs(self.repo_root)
        relevant_docs = select_docs_for_path(self.file_path, all_docs)
        docs_prompt = build_docs_prompt(relevant_docs, max_tokens=max_doc_tokens)
        if docs_prompt:
            sections.append(f"# Repository Documentation\n\n{docs_prompt}")

        # 2. AST context
        if enable_ast:
            ast_prompt = self._get_ast_context(max_ast_tokens)
            if ast_prompt:
                sections.append(f"# Code Structure\n\n{ast_prompt}")

        # 3. Repository map
        if enable_repo_map:
            map_prompt = self._get_repo_map(max_map_tokens)
            if map_prompt:
                sections.append(f"# Repository Context\n\n{map_prompt}")

        # 4. Similar code (embeddings)
        if enable_embeddings:
            similar_prompt = self._get_similar_code(
                max_embedding_tokens,
                use_mock=use_mock_embeddings,
            )
            if similar_prompt:
                sections.append(f"# Similar Code Patterns\n\n{similar_prompt}")

        # 5. Review instructions
        instructions = self._get_review_instructions(extra_instructions)
        sections.append(f"# Review Instructions\n\n{instructions}")

        return "\n\n---\n\n".join(sections)

    def _get_ast_context(self, max_tokens: int) -> str:
        """Extract AST context from the code being reviewed."""
        parser = ASTParser()
        context = parser.parse(self.code, language="python", file_path=self.file_path)
        return context.format_for_prompt(max_tokens=max_tokens)

    def _get_repo_map(self, max_tokens: int) -> str:
        """Generate repository map focused on the file being reviewed."""
        generator = RepoMapGenerator(self.repo_root)
        file_path = Path(self.file_path)
        if not file_path.is_absolute():
            file_path = self.repo_root / file_path

        repo_map = generator.generate(file_path, max_tokens=max_tokens)
        return repo_map.render(max_tokens=max_tokens)

    def _get_similar_code(self, max_tokens: int, use_mock: bool = False) -> str:
        """Find similar code via semantic search."""
        search = SemanticSearch(self.repo_root, use_mock=use_mock)

        # Run async search synchronously
        results = asyncio.run(search.find_similar(self.code, top_k=5, max_tokens=max_tokens))

        # Filter out results from the same file
        results.results = [r for r in results.results if r.chunk.file_path != self.file_path]

        return results.format(max_tokens=max_tokens)

    def _get_review_instructions(self, extra_instructions: str) -> str:
        """Generate the review instructions section."""
        base_instructions = """You are reviewing code for violations of the above repository guidelines and patterns.

When reviewing:
1. Check code against the documented conventions and anti-patterns
2. Compare with similar code patterns in the repository for consistency
3. Flag violations with severity: CRITICAL, HIGH, MEDIUM, LOW
4. Suggest simpler approaches when code is over-engineered
5. Be explicit about which guideline or pattern is being violated
6. Reference specific functions or patterns from the repository context when relevant"""

        if extra_instructions:
            return f"{base_instructions}\n\n{extra_instructions}"
        return base_instructions


def create_semantic_evaluator(
    repo_root: Path | str,
    file_path: str,
    code: str,
    models: list[ModelConfig] | None = None,
    enable_all: bool = False,
    **kwargs,
) -> SemanticEvaluator:
    """Convenience factory for creating a SemanticEvaluator.

    Args:
        repo_root: Path to the repository root.
        file_path: Path to the file being reviewed.
        code: The code being reviewed.
        models: List of models to use.
        enable_all: Enable all context types (including embeddings).
        **kwargs: Additional arguments passed to SemanticEvaluator.

    Returns:
        Configured SemanticEvaluator instance.
    """
    if enable_all:
        kwargs.setdefault("enable_ast", True)
        kwargs.setdefault("enable_repo_map", True)
        kwargs.setdefault("enable_embeddings", True)

    return SemanticEvaluator(
        repo_root=Path(repo_root),
        file_path=file_path,
        code=code,
        models=models,
        **kwargs,
    )
