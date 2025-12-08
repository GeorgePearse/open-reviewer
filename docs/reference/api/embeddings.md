# Embeddings

The embeddings module provides code chunking, vector generation, and storage for semantic code search.

## EmbeddingClient

Generates embeddings using OpenRouter's embedding models.

```python
from review_eval.semantic.embeddings import EmbeddingClient

client = EmbeddingClient(
    api_key="your-openrouter-key",
    model="qwen/qwen3-embedding-8b",
)

# Embed a single text
result = await client.embed_text("def authenticate(user): ...")
print(result.embedding)  # [0.123, -0.456, ...]
print(result.token_count)

# Embed multiple chunks
results = await client.embed_chunks([
    "def foo(): pass",
    "class Bar: pass",
])
```

### Constructor

```python
EmbeddingClient(
    api_key: str | None = None,
    model: str = "qwen/qwen3-embedding-8b",
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `api_key` | `str` | OpenRouter API key (default: OPENROUTER_API_KEY env) |
| `model` | `str` | Embedding model ID |

### Methods

#### embed_text

```python
async def embed_text(self, text: str) -> EmbeddingResult
```

Embed a single text string.

#### embed_chunks

```python
async def embed_chunks(
    self,
    chunks: list[str],
    batch_size: int = 100,
) -> list[EmbeddingResult]
```

Embed multiple chunks with batching.

### EmbeddingResult

```python
EmbeddingResult(
    embedding=[0.1, -0.2, ...],  # 1024-dimensional vector
    token_count=42,
)
```

---

## VectorStore

Stores and searches vectors using Qdrant.

```python
from review_eval.semantic.embeddings import VectorStore

store = VectorStore(
    url="https://your-cluster.qdrant.io:6333",
    api_key="your-key",
    collection_name="code_chunks",
)

# Add vectors
await store.add(
    ids=["chunk1", "chunk2"],
    vectors=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    payloads=[
        {"file_path": "a.py", "content": "..."},
        {"file_path": "b.py", "content": "..."},
    ],
)

# Search
results = await store.search(
    query_vector=[0.15, 0.25, ...],
    limit=5,
    min_score=0.5,
)
```

### Constructor

```python
VectorStore(
    url: str | None = None,
    api_key: str | None = None,
    collection_name: str = "code_chunks",
    vector_size: int = 1024,
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `str` | Qdrant URL (default: QDRANT_URL env) |
| `api_key` | `str` | Qdrant API key (default: QDRANT_API_KEY env) |
| `collection_name` | `str` | Collection name |
| `vector_size` | `int` | Vector dimensions |

### Methods

#### add

```python
async def add(
    self,
    ids: list[str],
    vectors: list[list[float]],
    payloads: list[dict],
) -> None
```

Add vectors with metadata.

#### search

```python
async def search(
    self,
    query_vector: list[float],
    limit: int = 5,
    min_score: float = 0.0,
) -> list[dict]
```

Search for similar vectors.

#### clear

```python
def clear(self) -> None
```

Delete all vectors in the collection.

---

## Code Chunking

Functions for splitting code into meaningful chunks for embedding.

```python
from review_eval.semantic.embeddings.chunker import (
    chunk_code,
    chunk_python_file,
    chunk_repository,
)
```

### chunk_code

```python
def chunk_code(
    code: str,
    language: str,
    file_path: str,
    max_chunk_size: int = 1000,
) -> list[CodeChunk]
```

Chunk code by semantic boundaries (functions, classes).

### chunk_python_file

```python
def chunk_python_file(
    file_path: str | Path,
    max_chunk_size: int = 1000,
) -> list[CodeChunk]
```

Chunk a Python file.

### chunk_repository

```python
def chunk_repository(
    repo_root: str | Path,
    languages: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> list[CodeChunk]
```

Chunk all code files in a repository.

| Parameter | Type | Description |
|-----------|------|-------------|
| `repo_root` | `Path` | Repository root directory |
| `languages` | `list[str]` | Languages to include (default: all supported) |
| `exclude_patterns` | `list[str]` | Glob patterns to exclude |

### Supported Languages

- Python (`.py`)
- TypeScript (`.ts`, `.tsx`)
- JavaScript (`.js`, `.jsx`)
- Rust (`.rs`)
- Go (`.go`)
- Java (`.java`)

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | API key for embedding generation |
| `QDRANT_URL` | Qdrant cluster URL |
| `QDRANT_API_KEY` | Qdrant API key |

---

## MockEmbeddingClient

For testing without API calls:

```python
from review_eval.semantic.embeddings import MockEmbeddingClient

client = MockEmbeddingClient(vector_size=1024)
result = await client.embed_text("test")
# Returns random vectors for testing
```
