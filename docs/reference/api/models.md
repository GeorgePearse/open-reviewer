# Data Models

All data models are Pydantic BaseModels for validation and serialization.

## ModelConfig

Configuration for a model to use in evaluation.

```python
from review_eval import ModelConfig

model = ModelConfig(
    name="Claude 3.5 Sonnet",
    model_id="anthropic/claude-3.5-sonnet",
    provider="openrouter",
    weight=0.9,
)
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | required | Human-readable name |
| `model_id` | `str` | required | Model identifier (e.g., `anthropic/claude-3.5-sonnet`) |
| `provider` | `str` | `"openrouter"` | Provider name |
| `weight` | `float` | `1.0` | Weight for consensus scoring |

---

## GoldenTestCase

A test case with known-bad code and expected findings.

```python
from review_eval import GoldenTestCase

test_case = GoldenTestCase(
    id="yaml-unsafe-load",
    file_path="fixtures/python/yaml_unsafe_load.py",
    code='''
import yaml

def load_config(path):
    with open(path) as f:
        return yaml.load(f)  # Unsafe!
''',
    expected_issues=["safe_load", "yaml.load"],
    severity="high",
    category="security",
)
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | required | Unique identifier |
| `file_path` | `str` | required | Path to fixture file (for reference) |
| `code` | `str` | required | Code snippet to review |
| `expected_issues` | `list[str]` | required | Keywords that MUST appear in review |
| `severity` | `str` | `"high"` | Expected severity level |
| `category` | `str` | required | Category (`python`, `typescript`, `sql`, `security`) |

---

## ReviewResult

Result from a single-model evaluation.

```python
from review_eval import ReviewResult

# Returned by ReviewEvaluator.evaluate()
result = ReviewResult(
    test_id="yaml-unsafe-load",
    passed=True,
    review_text="The code uses yaml.load() which is unsafe...",
    matched_issues=["safe_load", "yaml.load"],
    missed_issues=[],
)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `test_id` | `str` | ID of the evaluated test case |
| `passed` | `bool` | Whether all expected issues were found |
| `review_text` | `str` | Full text of the review response |
| `matched_issues` | `list[str]` | Issues correctly identified |
| `missed_issues` | `list[str]` | Issues the model failed to catch |

---

## ModelReviewResult

Result from a single model in a multi-model evaluation.

```python
from review_eval import ModelReviewResult

result = ModelReviewResult(
    model_name="Claude Opus 4.5",
    model_id="anthropic/claude-opus-4.5",
    review_text="This code has SQL injection vulnerabilities...",
    matched_issues=["SQL injection", "parameterized"],
    missed_issues=[],
    passed=True,
    latency_ms=1523.4,
)
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `model_name` | `str` | Human-readable model name |
| `model_id` | `str` | Full model identifier |
| `review_text` | `str` | The model's review response |
| `matched_issues` | `list[str]` | Issues correctly identified |
| `missed_issues` | `list[str]` | Issues the model missed |
| `passed` | `bool` | Whether all expected issues were found |
| `latency_ms` | `float` | Response time in milliseconds |

---

## MultiModelResult

Aggregated result from multiple models reviewing the same code.

```python
from review_eval import MultiModelResult

# Returned by MultiModelEvaluator.evaluate()
result: MultiModelResult

# Access consensus levels
print(result.unanimous_issues)  # Found by ALL models
print(result.consensus_issues)  # Found by majority
print(result.any_model_issues)  # Found by at least one

# Check pass rate
print(f"{result.pass_rate:.0%}")  # e.g., "100%"
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `test_id` | `str` | ID of the test case |
| `model_results` | `list[ModelReviewResult]` | Individual results from each model |
| `consensus_issues` | `list[str]` | Issues found by majority of models |
| `unanimous_issues` | `list[str]` | Issues found by ALL models |
| `any_model_issues` | `list[str]` | Issues found by at least one model |
| `consensus_passed` | `bool` | Whether consensus caught all expected issues |
| `models_passed` | `int` | Number of models that passed individually |
| `total_models` | `int` | Total number of models queried |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `pass_rate` | `float` | Percentage of models that passed (0.0 to 1.0) |

---

## Serialization

All models support Pydantic serialization:

```python
# To dict
data = result.model_dump()

# To JSON
json_str = result.model_dump_json()

# From dict
result = MultiModelResult.model_validate(data)

# From JSON
result = MultiModelResult.model_validate_json(json_str)
```
