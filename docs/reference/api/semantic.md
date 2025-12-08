# Semantic Analysis

The semantic analysis module provides code understanding through AST parsing, repository mapping, and code search.

## ASTParser

Parses Python code to extract structural information.

```python
from review_eval.semantic import ASTParser

parser = ASTParser()
context = parser.parse(
    code='''
def calculate_total(items: list[Item]) -> float:
    """Calculate the total price of items."""
    return sum(item.price for item in items)
''',
    language="python",
    file_path="cart.py",
)

print(context.functions)  # [FunctionSignature(...)]
print(context.classes)    # []
print(context.imports)    # []
```

### Methods

#### parse

```python
def parse(
    self,
    code: str,
    language: str,
    file_path: str | None = None,
) -> ASTContext
```

Parse code and extract AST context.

| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | `str` | Source code to parse |
| `language` | `str` | Language (`python`, `typescript`, `rust`, `go`, `java`) |
| `file_path` | `str` | Optional file path for context |

#### parse_file

```python
def parse_file(self, file_path: str | Path) -> ASTContext
```

Parse a file directly.

---

## RepoMapGenerator

Generates Aider-style repository maps showing key symbols and relationships.

```python
from review_eval.semantic import RepoMapGenerator

generator = RepoMapGenerator(repo_root="/path/to/repo")
repo_map = generator.generate(
    focus_file="src/api/handlers.py",
    max_tokens=2000,
    max_depth=3,
)

print(repo_map.content)
```

### Constructor

```python
RepoMapGenerator(repo_root: str | Path)
```

### Methods

#### generate

```python
def generate(
    self,
    focus_file: str | None = None,
    max_tokens: int = 2000,
    max_depth: int = 3,
) -> RepoMap
```

Generate a repository map.

| Parameter | Type | Description |
|-----------|------|-------------|
| `focus_file` | `str` | File to focus on (related symbols ranked higher) |
| `max_tokens` | `int` | Maximum tokens for the map |
| `max_depth` | `int` | Maximum directory depth to traverse |

---

## SemanticSearch

High-level semantic code search using embeddings.

```python
from review_eval.semantic import SemanticSearch

search = SemanticSearch(
    repo_root="/path/to/repo",
    qdrant_url="https://your-cluster.qdrant.io:6333",
    qdrant_api_key="your-key",
)

# Index the repository
await search.index_repository()

# Find similar code
results = await search.find_similar(
    query="authentication middleware",
    limit=5,
    min_similarity=0.5,
)

for result in results:
    print(f"{result.file_path}: {result.similarity:.2f}")
    print(result.content[:200])
```

### Constructor

```python
SemanticSearch(
    repo_root: str | Path,
    qdrant_url: str | None = None,
    qdrant_api_key: str | None = None,
    embedding_model: str = "qwen/qwen3-embedding-8b",
)
```

### Methods

#### index_repository

```python
async def index_repository(self) -> None
```

Index all code files in the repository.

#### find_similar

```python
async def find_similar(
    self,
    query: str,
    limit: int = 5,
    min_similarity: float = 0.5,
) -> list[SearchResult]
```

Find code similar to the query.

#### clear

```python
def clear(self) -> None
```

Clear the vector store.

---

## Data Models

### ASTContext

```python
from review_eval.semantic.models import ASTContext

context = ASTContext(
    functions=[...],
    classes=[...],
    imports=[...],
    file_path="example.py",
)
```

| Field | Type | Description |
|-------|------|-------------|
| `functions` | `list[FunctionSignature]` | Function definitions |
| `classes` | `list[ClassInfo]` | Class definitions |
| `imports` | `list[ImportInfo]` | Import statements |
| `file_path` | `str` | Source file path |

### FunctionSignature

```python
FunctionSignature(
    name="calculate_total",
    args=["items: list[Item]"],
    return_type="float",
    docstring="Calculate the total price of items.",
    line_number=1,
)
```

### ClassInfo

```python
ClassInfo(
    name="ShoppingCart",
    bases=["BaseModel"],
    methods=["add_item", "remove_item", "checkout"],
    docstring="Shopping cart model.",
    line_number=10,
)
```

### RepoMap

```python
RepoMap(
    content="src/\n  api/\n    handlers.py\n      def handle_request(...)\n",
    symbols=["handle_request", "validate_input"],
    token_count=450,
)
```

### SearchResult

```python
SearchResult(
    file_path="src/auth/middleware.py",
    content="def authenticate(request): ...",
    similarity=0.87,
    chunk_id="abc123",
)
```

### CodeChunk

Used internally by the chunker:

```python
CodeChunk(
    content="def foo(): pass",
    file_path="example.py",
    start_line=1,
    end_line=1,
    chunk_type="function",
    name="foo",
)
```
