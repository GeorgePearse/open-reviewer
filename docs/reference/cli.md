# CLI Tools

Command-line tools for PR quality scoring, repository indexing, and embedding management.

## score

Calculate PR quality score based on multiple metrics.

```bash
cd review_eval
uv run python -m review_eval score [OPTIONS]
```

### Usage

```bash
# Run scoring with all metrics
uv run python -m review_eval score \
  --config ../.github/reviewer-gate.yaml \
  --junit junit.xml \
  --coverage coverage.xml \
  --baseline-coverage 85.0 \
  --static-analysis ruff-results.json,pyright-results.json \
  --output pr-score.json \
  --fail-on-error

# Minimal scoring with just tests
uv run python -m review_eval score \
  --junit junit.xml \
  --threshold 70

# Custom threshold without config file
uv run python -m review_eval score \
  --junit junit.xml \
  --coverage coverage.xml \
  --baseline-coverage 85.0 \
  --threshold 75 \
  --fail-on-error
```

### Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Path to YAML configuration file (e.g., `.github/reviewer-gate.yaml`) |
| `--junit PATH` | Path to JUnit XML test results |
| `--coverage PATH` | Path to Cobertura XML coverage report |
| `--baseline-coverage FLOAT` | Baseline coverage percentage for delta calculation (0-100) |
| `--static-analysis PATH[,PATH]` | Comma-separated paths to ruff and pyright JSON outputs |
| `--ai-review PATH` | Path to AI review results JSON (future feature) |
| `--threshold FLOAT` | Minimum passing score (0-100). Overrides config. |
| `--output PATH` | Path to write JSON results (default: stdout) |
| `--fail-on-error` | Exit with code 1 if score below threshold |

### Configuration File

The `--config` option loads scoring configuration from a YAML file:

```yaml
scoring:
  threshold: 75

  weights:
    tests: 0.40
    coverage: 0.30
    static_analysis: 0.30
    ai_review: 0.00

  critical_penalties:
    security_vulnerability: 100
    critical_test_failure: 50

  tolerance:
    coverage_delta: 0.1
```

See [PR Quality Gate Setup](../how-to/pr-quality-gate.md) for configuration details.

### Output Format

**JSON Output** (`--output pr-score.json`):

```json
{
  "total_score": 87.5,
  "status": "PASS",
  "threshold": 75,
  "blocking_factors": [],
  "breakdown": {
    "tests": {
      "category": "tests",
      "raw_value": 95.0,
      "normalized_score": 95.0,
      "weight": 0.4,
      "details": {
        "passed": 38,
        "total": 40
      }
    },
    "coverage": {
      "category": "coverage",
      "raw_value": 2.5,
      "normalized_score": 82.0,
      "weight": 0.3,
      "details": {
        "delta": "+2.5%"
      }
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Console Output**:

```
PR Quality Score: 87.5/100

Status: PASS (threshold: 75)

Breakdown:
  Tests:            95.0/100 (weight: 40%) - 38/40 passed
  Coverage:         82.0/100 (weight: 30%) - +2.5%
  Static Analysis:  85.0/100 (weight: 30%) - 3 errors
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Score above threshold or `--fail-on-error` not set |
| 1 | Score below threshold and `--fail-on-error` set |
| 2 | Invalid arguments or configuration error |

### Examples

**Local Testing**:

```bash
cd review_eval

# Generate test reports
uv run pytest --junitxml=junit.xml --cov --cov-report=xml

# Generate static analysis reports
uv run ruff check . --output-format json > ruff-results.json
uv run pyright --outputjson > pyright-results.json

# Calculate score
uv run python -m review_eval score \
  --config ../.github/reviewer-gate.yaml \
  --junit junit.xml \
  --coverage coverage.xml \
  --baseline-coverage 85.0 \
  --static-analysis ruff-results.json,pyright-results.json
```

**GitHub Actions**:

```yaml
- name: Calculate PR Score
  run: |
    cd review_eval
    uv run python -m review_eval score \
      --config ../.github/reviewer-gate.yaml \
      --junit junit.xml \
      --coverage coverage.xml \
      --baseline-coverage ${{ steps.baseline.outputs.baseline_coverage }} \
      --static-analysis ruff-results.json,pyright-results.json \
      --output pr-score.json \
      --fail-on-error
```

See [PR Quality Gate](../how-to/pr-quality-gate.md) for complete setup instructions.

---

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
