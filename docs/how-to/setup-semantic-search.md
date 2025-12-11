# Setup Semantic Search

Enable embedding-based code similarity search for enhanced reviews.

## What is Semantic Search?

Semantic search finds code that is conceptually similar to the code being reviewed, even if it uses different variable names or structure. This helps reviewers:

- See how similar problems were solved elsewhere
- Identify inconsistent patterns
- Understand existing conventions

## Prerequisites

- OpenRouter API key (for embeddings)
- Qdrant Cloud account (for vector storage)

## Step 1: Create Qdrant Cloud Cluster

1. Go to [qdrant.io](https://qdrant.io) and sign up
2. Create a new cluster (free tier available)
3. Note your cluster URL and API key

## Step 2: Set Environment Variables

```bash
export OPENROUTER_API_KEY="sk-or-..."
export QDRANT_URL="https://your-cluster.qdrant.io:6333"
export QDRANT_API_KEY="your-qdrant-key"
```

## Step 3: Index Your Repository

```bash
cd review_eval
uv run python -m review_eval.index_repo /path/to/your/repo --force
```

This will:

1. Chunk all code files by semantic boundaries (functions, classes)
2. Generate embeddings using OpenRouter
3. Store vectors in Qdrant

Output:

```
Indexing /path/to/your/repo...
  - Chunking Python files
  - Generating embeddings via OpenRouter (qwen/qwen3-embedding-8b)
  - Storing vectors in Qdrant (batched uploads)

Found 5000 chunks, generating embeddings...
Uploading 5000 vectors to Qdrant...
Indexed 4892 chunks in 312.0s
```

## Step 4: Use in Evaluator

### With SemanticEvaluator

```python
from review_eval import create_semantic_evaluator

evaluator = create_semantic_evaluator(
    repo_root="/path/to/repo",
    file_path="src/auth/login.py",
    code=code_to_review,
    enable_embeddings=True,  # Enable semantic search
)

result = evaluator.evaluate(test_case)
```

### Direct Search

```python
from review_eval.semantic import SemanticSearch

search = SemanticSearch(
    repo_root="/path/to/repo",
    qdrant_url="https://your-cluster.qdrant.io:6333",
    qdrant_api_key="your-key",
)

# Find similar code
results = await search.find_similar(
    query="def authenticate(username, password):",
    limit=5,
    min_similarity=0.5,
)

for result in results:
    print(f"{result.file_path}: {result.similarity:.2f}")
    print(result.content[:100])
```

## Step 5: Keep Embeddings Updated

### Manual Update

After code changes:

```bash
uv run python -m review_eval.update_embeddings /path/to/repo
```

### Automated Update (GitHub Actions)

Add to your workflow:

```yaml
- name: Update embeddings
  run: |
    cd review_eval
    uv run python -m review_eval.update_embeddings ${{ github.workspace }}
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    QDRANT_URL: ${{ secrets.QDRANT_URL }}
    QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
```

## Configuration Options

### Change Embedding Model

```python
from review_eval.semantic.embeddings import EmbeddingClient

client = EmbeddingClient(
    model="text-embedding-3-small",  # Different model
)
```

### Adjust Token Budget

```python
evaluator = create_semantic_evaluator(
    repo_root=repo,
    file_path=file,
    code=code,
    similar_code_budget=12000,  # More similar code context
)
```

### Custom Similarity Threshold

```python
results = await search.find_similar(
    query=code,
    limit=10,
    min_similarity=0.7,  # Higher threshold = more relevant
)
```

## Supported Languages

The chunker supports:

- Python (`.py`)
- TypeScript (`.ts`, `.tsx`)
- JavaScript (`.js`, `.jsx`)
- Rust (`.rs`)
- Go (`.go`)
- Java (`.java`)

## Troubleshooting

### "QDRANT_URL not set"

```bash
export QDRANT_URL="https://your-cluster.qdrant.io:6333"
```

### "Collection not found"

Run indexing first:

```bash
uv run python -m review_eval.index_repo /path/to/repo --force
```

### Slow indexing

Large repositories take time. The indexer processes ~16 chunks/second.

For faster iteration, index a subset:

```python
from review_eval.semantic.embeddings.chunker import chunk_repository

chunks = chunk_repository(
    repo_root,
    languages=["python"],  # Only Python
    exclude_patterns=["**/tests/**"],  # Skip tests
)
```

### High costs

Embedding generation costs are low but scale with codebase size.

For development, use a smaller test repository.
