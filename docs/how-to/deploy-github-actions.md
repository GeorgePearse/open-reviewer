# Deploy GitHub Actions

Set up automated PR reviews using Open Reviewer.

## Quick Setup

1. Copy the workflow files
2. Add secrets to your repository
3. Create guidelines files
4. Open a PR to test

## Step 1: Add Workflow File

Create `.github/workflows/review.yml`:

```yaml
name: Claude Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get changed files
        id: changed
        run: |
          echo "files=$(git diff --name-only ${{ github.event.pull_request.base.sha }} ${{ github.event.pull_request.head.sha }} | tr '\n' ' ')" >> $GITHUB_OUTPUT

      - name: Review code
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Review the following changed files for issues:
            ${{ steps.changed.outputs.files }}

            Check for:
            - Code quality issues
            - Potential bugs
            - Security vulnerabilities
            - Style violations
```

## Step 2: Add Secrets

Go to Settings > Secrets and variables > Actions.

Add:

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `OPENROUTER_API_KEY` | Your OpenRouter API key (optional) |
| `QDRANT_API_KEY` | Your Qdrant API key (optional) |

## Step 3: Add Guidelines Files

### CLAUDE.md (Repository Root)

```markdown
# Code Review Guidelines

## Style
- Use type annotations
- Maximum function length: 50 lines
- Descriptive variable names

## Security
- No hardcoded secrets
- Parameterized queries only
- Validate user input
```

### AGENTS.md (Per Directory)

Create in specific directories for domain rules:

```markdown
# backend/AGENTS.md

## API Guidelines
- Use Pydantic for validation
- Return proper HTTP codes
- Document with OpenAPI
```

## Step 4: Test

1. Create a branch
2. Make a code change
3. Open a PR
4. Check the Actions tab

## Advanced Configuration

### Filter by File Type

```yaml
on:
  pull_request:
    paths:
      - '**.py'
      - '**.ts'
      - '**.js'
```

### Add Security Review

```yaml
jobs:
  review:
    # ... main review job

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Security review
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Focus on OWASP Top 10 vulnerabilities:
            - Injection attacks
            - Authentication issues
            - Data exposure
```

### Enable @claude Mentions

```yaml
on:
  pull_request:
  issue_comment:
    types: [created]

jobs:
  handle-mention:
    if: contains(github.event.comment.body, '@claude')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Respond to mention
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Add Semantic Search Context

First, set up Qdrant and index your repo (see [Setup Semantic Search](setup-semantic-search.md)).

Then add to workflow:

```yaml
- name: Fetch similar code
  run: |
    cd review_eval
    uv run python .github/scripts/fetch_similar_code.py \
      --query "${{ steps.changed.outputs.files }}" \
      > similar_code.txt
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    QDRANT_URL: ${{ secrets.QDRANT_URL }}
    QDRANT_API_KEY: ${{ secrets.QDRANT_API_KEY }}

- name: Review with context
  uses: anthropics/claude-code-action@v1
  with:
    prompt: |
      Similar code in repository:
      $(cat similar_code.txt)

      Review the changed files...
```

## Multi-Stage Review

For large PRs, review in stages:

```yaml
jobs:
  prepare:
    outputs:
      matrix: ${{ steps.generate.outputs.matrix }}
    steps:
      - name: Generate chunk matrix
        id: generate
        run: |
          # Split changed files into chunks
          echo "matrix=[{\"chunk\":1},{\"chunk\":2}]" >> $GITHUB_OUTPUT

  review:
    needs: prepare
    strategy:
      matrix: ${{ fromJson(needs.prepare.outputs.matrix) }}
    steps:
      - name: Review chunk ${{ matrix.chunk }}
        uses: anthropics/claude-code-action@v1
```

## Troubleshooting

### Reviews not appearing

1. Check Actions tab for errors
2. Verify secrets are set
3. Ensure `pull-requests: write` permission

### Rate limits

Reduce parallel reviews:

```yaml
strategy:
  max-parallel: 2
```

### Long review times

Use faster models:

```yaml
with:
  model: claude-3.5-haiku
```

### Large diffs

Skip review for large PRs:

```yaml
- name: Check size
  run: |
    LINES=$(git diff --stat ${{ github.event.pull_request.base.sha }} | tail -1 | awk '{print $4}')
    if [ "$LINES" -gt 1000 ]; then
      echo "PR too large for review"
      exit 0
    fi
```

## Best Practices

1. **Start simple** - Basic review first, add features gradually
2. **Use guidelines** - CLAUDE.md makes reviews more relevant
3. **Set expectations** - Reviews are suggestions, not approvals
4. **Monitor costs** - Watch API usage in the first weeks
5. **Iterate** - Refine prompts based on review quality
