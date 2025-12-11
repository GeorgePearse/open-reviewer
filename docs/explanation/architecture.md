# Architecture

Open Reviewer is designed as a layered system that combines multiple AI models with rich code context.

## System Overview

```mermaid
flowchart TB
    subgraph Input
        Code[Code to Review]
        TC[Test Cases]
    end

    subgraph Context["Context Providers"]
        direction TB
        Docs[Documentation<br/>CLAUDE.md / AGENTS.md]
        AST[AST Parser<br/>Functions, Classes]
        Map[Repo Map<br/>Symbol Relationships]
        Emb[Embeddings<br/>Similar Code]
    end

    subgraph Evaluation
        direction TB
        SE[SemanticEvaluator]
        MME[MultiModelEvaluator]
        subgraph Models["Parallel Model Queries"]
            M1[Claude]
            M2[GPT]
            M3[Gemini]
            M4[DeepSeek]
        end
    end

    subgraph Output
        Cons[Consensus Analysis]
        Rep[Report Generation]
    end

    Input --> Context
    Context --> SE
    SE --> MME
    MME --> Models
    Models --> Cons
    Cons --> Rep
```

## Core Components

### Evaluators

The evaluation layer is built on inheritance:

1. **ReviewEvaluator** - Base evaluator using Anthropic API directly
2. **MultiModelEvaluator** - Parallel querying of multiple models via OpenRouter
3. **DocsAwareEvaluator** - Adds documentation context
4. **SemanticEvaluator** - Adds AST, repo map, and embedding context

### Context Providers

Four types of context enhance review quality:

| Provider | Source | Purpose |
|----------|--------|---------|
| Documentation | CLAUDE.md, AGENTS.md | Project-specific guidelines |
| AST Context | Python AST parser | Function signatures, class structure |
| Repository Map | Code analysis | Key symbols and relationships |
| Similar Code | Vector embeddings | Related code patterns |

### Consensus Engine

The consensus engine aggregates findings from multiple models:

```mermaid
flowchart LR
    subgraph Models
        M1[Claude<br/>Found: A, B]
        M2[GPT<br/>Found: A, C]
        M3[Gemini<br/>Found: A, B, C]
    end

    subgraph Aggregation
        Count[Issue Counts<br/>A: 3, B: 2, C: 2]
    end

    subgraph Consensus
        U[Unanimous<br/>A]
        Maj[Majority<br/>A, B, C]
        Any[Any<br/>A, B, C]
    end

    Models --> Count
    Count --> Consensus
```

## Data Flow

### 1. Input Processing

```python
test_case = GoldenTestCase(
    id="example",
    code="...",
    expected_issues=["keyword1", "keyword2"],
)
```

### 2. Context Gathering

The SemanticEvaluator gathers context from multiple sources:

```python
# Documentation context (15K tokens)
docs = discover_docs(repo_root)
relevant_docs = select_docs_for_path(docs, file_path)

# AST context (3K tokens)
ast_context = ast_parser.parse(code, "python")

# Repository map (2K tokens)
repo_map = map_generator.generate(focus_file=file_path)

# Similar code (8K tokens)
similar = await semantic_search.find_similar(code)
```

### 3. Prompt Construction

Context is combined into a single prompt with token budgets:

```
[System: Review Instructions]
[Documentation: CLAUDE.md, AGENTS.md content]
[AST: Function signatures, class definitions]
[Repo Map: Key symbols in codebase]
[Similar Code: Related implementations]
[User: Code to review]
```

### 4. Parallel Model Queries

```python
tasks = [
    evaluate_model(claude, prompt),
    evaluate_model(gpt, prompt),
    evaluate_model(gemini, prompt),
]
results = await asyncio.gather(*tasks)
```

### 5. Consensus Calculation

```python
# Count issue occurrences
issue_counts = Counter(all_matched_issues)
total_models = len(models)
majority_threshold = total_models // 2 + 1

# Determine consensus levels
unanimous = [i for i, c in counts.items() if c == total_models]
majority = [i for i, c in counts.items() if c >= majority_threshold]
any_model = list(counts.keys())
```

## Integration Points

### GitHub Actions

```mermaid
flowchart LR
    PR[Pull Request] --> Prepare[Parse AGENTS.md<br/>Filter Chunks]
    Prepare --> Matrix[Generate Matrix]
    Matrix --> Review[Parallel Reviews]
    Review --> Security[Security Check]
    Security --> Comments[Post Comments]
```

### Qdrant Vector Store

```mermaid
flowchart TB
    Code[Repository Code] --> Chunk[Chunker]
    Chunk --> Embed[Embedding Client]
    Embed --> Store[Qdrant Cloud]

    Query[Review Query] --> QEmbed[Query Embedding]
    QEmbed --> Search[Vector Search]
    Store --> Search
    Search --> Similar[Similar Code]
```

## Extension Points

### Custom Models

Add new models by creating ModelConfig:

```python
custom_model = ModelConfig(
    name="My Model",
    model_id="provider/model-id",
    weight=1.0,
)
```

### Custom Context Providers

Extend SemanticEvaluator to add new context sources by overriding `_build_prompt()`.

### Custom Consensus Logic

Subclass MultiModelEvaluator to implement weighted voting or other consensus algorithms.
