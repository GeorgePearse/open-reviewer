"""Review evaluation package for testing Claude Code review quality."""

from review_eval.docs_aware_evaluator import DocsAwareEvaluator
from review_eval.docs_loader import (
    DocumentationFile,
    build_docs_prompt,
    discover_docs,
    get_doc_coverage_report,
    select_docs_for_path,
)
from review_eval.evaluator import ReviewEvaluator
from review_eval.models import (
    GoldenTestCase,
    ModelConfig,
    ModelReviewResult,
    MultiModelResult,
    ReviewResult,
)
from review_eval.multi_model_evaluator import (
    BENCHMARK_MODELS,
    DEFAULT_MODELS,
    MultiModelEvaluator,
    print_multi_model_report,
)
from review_eval.semantic_evaluator import SemanticEvaluator, create_semantic_evaluator

__all__ = [
    "BENCHMARK_MODELS",
    "DEFAULT_MODELS",
    "DocsAwareEvaluator",
    "DocumentationFile",
    "GoldenTestCase",
    "ModelConfig",
    "ModelReviewResult",
    "MultiModelEvaluator",
    "MultiModelResult",
    "ReviewEvaluator",
    "ReviewResult",
    "SemanticEvaluator",
    "build_docs_prompt",
    "create_semantic_evaluator",
    "discover_docs",
    "get_doc_coverage_report",
    "print_multi_model_report",
    "select_docs_for_path",
]
