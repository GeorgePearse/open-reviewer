"""Documentation-aware evaluator that injects CLAUDE.md/AGENTS.md into prompts."""

from pathlib import Path

from review_eval.docs_loader import (
    build_docs_prompt,
    discover_docs,
    select_docs_for_path,
)
from review_eval.models import ModelConfig
from review_eval.multi_model_evaluator import MultiModelEvaluator


class DocsAwareEvaluator(MultiModelEvaluator):
    """Evaluator that automatically injects relevant repository documentation.

    This evaluator discovers CLAUDE.md and AGENTS.md files in the repository
    and includes relevant documentation based on the file path being reviewed.

    Attributes:
        repo_root: Path to the repository root.
        file_path: Path to the file being reviewed.
    """

    def __init__(
        self,
        repo_root: Path,
        file_path: str,
        models: list[ModelConfig] | None = None,
        extra_instructions: str = "",
        api_key: str | None = None,
        max_doc_tokens: int = 25000,
    ) -> None:
        """Initialize the docs-aware evaluator.

        Args:
            repo_root: Path to the repository root.
            file_path: Path to the file being reviewed (relative to repo root).
            models: List of models to use (defaults to DEFAULT_MODELS).
            extra_instructions: Additional review instructions to append.
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var).
            max_doc_tokens: Maximum tokens for documentation (default 25000).
        """
        self.repo_root = repo_root
        self.file_path = file_path

        # Discover and select relevant docs
        all_docs = discover_docs(repo_root)
        relevant_docs = select_docs_for_path(file_path, all_docs)
        docs_prompt = build_docs_prompt(relevant_docs, max_tokens=max_doc_tokens)

        # Build the full prompt
        prompt = f"""{docs_prompt}

---

## Review Instructions

You are reviewing code for violations of the above repository guidelines.

When reviewing:
1. Check code against the documented conventions and anti-patterns
2. Flag violations with severity: CRITICAL, HIGH, MEDIUM, LOW
3. Suggest simpler approaches when code is over-engineered
4. Be explicit about which guideline is being violated

{extra_instructions}""".strip()

        super().__init__(prompt, models, api_key)
