# API Overview

The Open Reviewer API is organized into four main areas:

## Core Components

| Module | Description |
|--------|-------------|
| [Evaluators](evaluators.md) | Core evaluation classes for single and multi-model review |
| [Data Models](models.md) | Pydantic models for test cases, results, and configuration |
| [Semantic Analysis](semantic.md) | AST parsing, repository mapping, and code search |
| [Embeddings](embeddings.md) | Vector storage and embedding generation |

## Quick Import

```python
from review_eval import (
    # Core evaluators
    ReviewEvaluator,
    MultiModelEvaluator,
    DocsAwareEvaluator,
    SemanticEvaluator,
    create_semantic_evaluator,

    # Data models
    GoldenTestCase,
    ModelConfig,
    ModelReviewResult,
    MultiModelResult,
    ReviewResult,

    # Model configurations
    DEFAULT_MODELS,
    BENCHMARK_MODELS,

    # Utilities
    print_multi_model_report,
)
```

## Package Structure

```
review_eval/
├── __init__.py              # Public API exports
├── evaluator.py             # ReviewEvaluator
├── multi_model_evaluator.py # MultiModelEvaluator
├── docs_aware_evaluator.py  # DocsAwareEvaluator
├── semantic_evaluator.py    # SemanticEvaluator
├── models.py                # Pydantic data models
├── docs_loader.py           # Documentation discovery
├── index_repo.py            # CLI: index repository
├── update_embeddings.py     # CLI: update embeddings
└── semantic/
    ├── ast_parser.py        # Python AST parsing
    ├── repo_map.py          # Repository mapping
    ├── search.py            # Semantic search
    ├── models.py            # Semantic data models
    └── embeddings/
        ├── chunker.py       # Code chunking
        ├── client.py        # Embedding client
        └── vector_store.py  # Qdrant integration
```
