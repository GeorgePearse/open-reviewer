# Index Repository

Index your codebase for semantic code search.

## Quick Start

```bash
cd review_eval
export OPENROUTER_API_KEY="..."
export QDRANT_URL="https://your-cluster.qdrant.io:6333"
export QDRANT_API_KEY="..."

uv run python -m review_eval.index_repo /path/to/repo --force
```

## What Indexing Does

1. **Scans** the repository for code files
2. **Chunks** code by semantic boundaries (functions, classes)
3. **Generates embeddings** using OpenRouter's embedding model
4. **Stores vectors** in Qdrant for fast similarity search

## Command Options

### Basic Indexing

```bash
uv run python -m review_eval.index_repo /path/to/repo
```

### Force Re-index

Delete existing vectors and re-index:

```bash
uv run python -m review_eval.index_repo /path/to/repo --force
```

### Count Only

See how many chunks without indexing:

```bash
uv run python -m review_eval.index_repo /path/to/repo --count-only
```

Output:

```
Chunking repository: /path/to/repo
Found 5432 chunks
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | For embedding generation |
| `QDRANT_URL` | Yes | Qdrant cluster URL |
| `QDRANT_API_KEY` | Yes | Qdrant authentication |

## Example Output

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

## Incremental Updates

After code changes, update only changed files:

```bash
uv run python -m review_eval.update_embeddings /path/to/repo
```

This is faster than full re-indexing.

## Indexing in CI/CD

### GitHub Actions Workflow

```yaml
name: Index Repository

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * 0'  # Weekly

jobs:
  index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          cd review_eval && uv sync

      - name: Index repository
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          QDRANT_URL: ${{ secrets.QDRANT_URL }}
          QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}
        run: |
          cd review_eval
          uv run python -m review_eval.index_repo ${{ github.workspace }} --force
```

## Supported File Types

| Language | Extensions |
|----------|------------|
| Python | `.py` |
| TypeScript | `.ts`, `.tsx` |
| JavaScript | `.js`, `.jsx` |
| Rust | `.rs` |
| Go | `.go` |
| Java | `.java` |

## Performance Tips

### Large Repositories

For repositories with 10,000+ files:

1. Start with a subset:
   ```bash
   # Index only src/
   uv run python -m review_eval.index_repo /path/to/repo/src
   ```

2. Exclude test files (they add noise):
   - Modify chunker to skip `**/tests/**`

3. Run overnight or on schedule

### Optimizing Chunk Count

More chunks = more granular search but higher costs.

Default chunking creates chunks for:
- Each function
- Each class
- Each method within classes

## Troubleshooting

### "Rate limit exceeded"

OpenRouter has rate limits. The indexer handles this with retries, but for large repos:

```bash
# Run in smaller batches
uv run python -m review_eval.index_repo /path/to/repo/src
uv run python -m review_eval.index_repo /path/to/repo/lib
```

### "Connection refused" (Qdrant)

Verify your Qdrant URL:

```bash
curl -H "api-key: $QDRANT_API_KEY" "$QDRANT_URL/collections"
```

### Missing files

Check the supported file types. Non-code files (markdown, config) are skipped.

### Stale embeddings

Re-run with `--force` to refresh:

```bash
uv run python -m review_eval.index_repo /path/to/repo --force
```
