# CLI Tools

Command-line tools for repository indexing and embedding management.

## index_repo

Index a repository for semantic code search.

```bash
cd review_eval
uv run python -m review_eval.index_repo /path/to/repo [OPTIONS]
```

### Usage

```bash
# Index a repository
uv run python -m review_eval.index_repo /path/to/repo

# Force re-index (delete existing vectors)
uv run python -m review_eval.index_repo /path/to/repo --force

# Count chunks without indexing
uv run python -m review_eval.index_repo /path/to/repo --count-only
```

### Options

| Option | Description |
|--------|-------------|
| `--force` | Delete existing collection and re-index |
| `--count-only` | Only count chunks, don't generate embeddings |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | API key for embedding generation |
| `QDRANT_URL` | Yes | Qdrant cluster URL |
| `QDRANT_API_KEY` | Yes | Qdrant API key |

### Output

```
Indexing /path/to/repo...
  - Chunking Python files
  - Generating embeddings via OpenRouter (qwen/qwen3-embedding-8b)
  - Storing vectors in Qdrant (batched uploads)

Chunking repository: /path/to/repo
Found 10000 chunks, generating embeddings...
Uploading 10000 vectors to Qdrant...
Indexed 9938 chunks

Indexed 9938 chunks in 622.0s
Average: 16.0 chunks/sec
```

---

## update_embeddings

Incrementally update embeddings for changed files.

```bash
uv run python -m review_eval.update_embeddings /path/to/repo [OPTIONS]
```

### Usage

```bash
# Update embeddings for files changed since last commit
uv run python -m review_eval.update_embeddings /path/to/repo

# Update embeddings for files changed in last N commits
uv run python -m review_eval.update_embeddings /path/to/repo --commits 5

# Dry run - show what would be updated
uv run python -m review_eval.update_embeddings /path/to/repo --dry-run
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--commits N` | 1 | Number of commits to check for changes |
| `--dry-run` | false | Show what would be updated without making changes |

### How It Works

1. Uses `git diff` to find changed Python files
2. Re-chunks only the changed files
3. Deletes old vectors for those files from Qdrant
4. Generates new embeddings and uploads them

This is much faster than full re-indexing for incremental updates.

---

## Running in CI/CD

### GitHub Actions Example

```yaml
- name: Update embeddings
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    QDRANT_URL: ${{ secrets.QDRANT_URL }}
    QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
  run: |
    cd review_eval
    uv run python -m review_eval.update_embeddings ${{ github.workspace }}
```

### Initial Indexing Workflow

```yaml
name: Index Repository

on:
  workflow_dispatch:  # Manual trigger

jobs:
  index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        run: pip install uv

      - name: Index repository
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          QDRANT_URL: ${{ secrets.QDRANT_URL }}
          QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
        run: |
          cd review_eval
          uv sync
          uv run python -m review_eval.index_repo ${{ github.workspace }} --force
```
