# Review Eval

Golden test suite for verifying Claude Code review quality.

## Purpose

This package contains known-bad code snippets (golden tests) to verify that Claude correctly identifies anti-patterns specific to the BinIt codebase.

## Installation

```bash
cd lib/python/review_eval
uv sync
```

## Running Tests

### Single Model (Claude via Anthropic API)

```bash
export ANTHROPIC_API_KEY="your-key-here"
uv run pytest -v -k "not multi_model"
```

### Multi-Model Consensus (via OpenRouter)

```bash
export OPENROUTER_API_KEY="your-key-here"
uv run pytest -v -k "multi_model"
```

## Multi-Model Evaluation

Get consensus from multiple top models via OpenRouter:

```python
from review_eval import MultiModelEvaluator, GoldenTestCase, print_multi_model_report

evaluator = MultiModelEvaluator(
    prompt_context="Review this code for security issues...",
    # Uses Claude 3.5 Sonnet, GPT-4o, Gemini 2.0, DeepSeek V3, Llama 3.3 by default
)

test_case = GoldenTestCase(
    id="test-sql-injection",
    file_path="example.py",
    code="query = f'SELECT * FROM users WHERE id = {user_id}'",
    expected_issues=["SQL injection", "parameterized"],
    category="security",
)

result = evaluator.evaluate(test_case)
print_multi_model_report(result)
```

Output:

```
============================================================
Test: test-sql-injection
============================================================
Pass Rate: 5/5 (100%)
Consensus Passed: ✓

Individual Model Results:
----------------------------------------
  ✓ Claude 3.5 Sonnet (1234ms)
     Caught: SQL injection, parameterized
  ✓ GPT-4o (892ms)
     Caught: SQL injection, parameterized
  ✓ Gemini 2.0 Flash (456ms)
     Caught: SQL injection, parameterized
  ...

Aggregated Findings:
----------------------------------------
  Unanimous (all models): ['SQL injection', 'parameterized']
  Consensus (majority):   ['SQL injection', 'parameterized']
  Any model found:        ['SQL injection', 'parameterized', 'f-string']
```

### Default Models (Production)

| Model           | Provider  |
| --------------- | --------- |
| Claude Opus 4.5 | Anthropic |
| GPT-5.1 Codex   | OpenAI    |
| Gemini 3 Pro    | Google    |

### Benchmark Models (13 models for comprehensive testing)

Use `BENCHMARK_MODELS` for full evaluation across model tiers:

```python
from review_eval import MultiModelEvaluator, BENCHMARK_MODELS

evaluator = MultiModelEvaluator(prompt, models=BENCHMARK_MODELS)
```

| Tier                    | Models                                                  |
| ----------------------- | ------------------------------------------------------- |
| **Tier 1: Frontier**    | Claude Opus 4.5, GPT-5.1 Codex, Gemini 3 Pro            |
| **Tier 2: Production**  | Claude 3.5 Sonnet, GPT-4o, Gemini 2.5 Pro               |
| **Tier 3: Fast**        | Claude 3.5 Haiku, GPT-4o Mini, Gemini 2.0 Flash         |
| **Tier 4: Alternative** | DeepSeek V3, Llama 3.3 70B, Qwen 2.5 72B, Mistral Large |

Customize models:

```python
from review_eval import MultiModelEvaluator, ModelConfig

my_models = [
    ModelConfig(name="Claude", model_id="anthropic/claude-3.5-sonnet"),
    ModelConfig(name="GPT-4", model_id="openai/gpt-4-turbo"),
]

evaluator = MultiModelEvaluator(prompt, models=my_models)
```

## Test Categories

### Python Anti-Patterns

- `psycopg2` instead of `psycopg3`
- `yaml.load()` instead of `yaml.safe_load()`
- Missing type annotations
- `Any` types without justification
- `utils`/`misc` modules

### TypeScript Anti-Patterns

- Raw `fetch()` instead of `apiFetch`/`getJson` helpers
- `any` types
- Default exports (prefer named)
- Direct Postgres queries (use GraphQL)

### SQL Anti-Patterns

- Boolean columns without `is_` prefix
- `varchar(n)` instead of `TEXT`
- `SELECT *` instead of explicit columns
- `TIMESTAMP` without `TIME ZONE`

### Security Issues

- SQL injection via string formatting
- Hardcoded secrets/API keys
- Command injection (`shell=True`)

## Adding New Test Cases

1. Add a fixture file in `review_eval/fixtures/<category>/`
2. Add a test in `tests/test_<category>_patterns.py`
3. Define expected issues that Claude should catch

Example:

```python
test_case = GoldenTestCase(
    id="python-new-antipattern",
    file_path="fixtures/python/new_antipattern.py",
    code=code,
    expected_issues=["keyword1", "keyword2"],
    category="python",
)
result = evaluator.evaluate(test_case)
assert result.passed
```
