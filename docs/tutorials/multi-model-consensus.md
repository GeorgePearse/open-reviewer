# Multi-Model Consensus

Learn how to use multiple AI models for higher-confidence code reviews.

## Why Multi-Model?

Single models can:

- Have blind spots
- Be biased by training data
- Produce inconsistent results

Using multiple models and aggregating their findings gives you:

- **Higher confidence** when models agree
- **Better coverage** from diverse perspectives
- **Measurable reliability** through consensus levels

## Prerequisites

- Completed [Your First Evaluation](first-evaluation.md)
- An OpenRouter API key (get one at [openrouter.ai](https://openrouter.ai))

## Step 1: Set Up OpenRouter

Export your OpenRouter API key:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

OpenRouter provides access to multiple AI models through a single API.

## Step 2: Your First Multi-Model Evaluation

```python
from review_eval import MultiModelEvaluator, GoldenTestCase, DEFAULT_MODELS

# Create a test case
test_case = GoldenTestCase(
    id="sql-injection",
    file_path="query.py",
    code='''
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
''',
    expected_issues=["SQL injection", "parameterized"],
    category="security",
)

# Create a multi-model evaluator
evaluator = MultiModelEvaluator(
    prompt_context="Review this code for security vulnerabilities.",
    models=DEFAULT_MODELS,  # Claude, GPT, Gemini
)

# Run the evaluation
result = evaluator.evaluate(test_case)

# Print results
print(f"Pass Rate: {result.models_passed}/{result.total_models}")
print(f"Unanimous Issues: {result.unanimous_issues}")
print(f"Majority Issues: {result.consensus_issues}")
print(f"Any Model Found: {result.any_model_issues}")
```

## Step 3: Understanding the Results

### Consensus Levels

```python
result.unanimous_issues   # Found by ALL models
result.consensus_issues   # Found by MAJORITY of models
result.any_model_issues   # Found by at least ONE model
```

### Individual Model Results

```python
for model_result in result.model_results:
    print(f"{model_result.model_name}:")
    print(f"  Passed: {model_result.passed}")
    print(f"  Matched: {model_result.matched_issues}")
    print(f"  Latency: {model_result.latency_ms:.0f}ms")
```

### Pass Rate

```python
print(f"Pass Rate: {result.pass_rate:.0%}")  # e.g., "100%"
```

## Step 4: Use the Report Function

For formatted output:

```python
from review_eval import print_multi_model_report

result = evaluator.evaluate(test_case)
print_multi_model_report(result)
```

Output:

```
============================================================
Test: sql-injection
============================================================
Pass Rate: 3/3 (100%)
Consensus Passed: ✓

Individual Model Results:
----------------------------------------
  ✓ Claude Opus 4.5 (1523ms)
     Caught: SQL injection, parameterized
  ✓ GPT-5.1 Codex (892ms)
     Caught: SQL injection, parameterized
  ✓ Gemini 3 Pro (1102ms)
     Caught: SQL injection, parameterized

Aggregated Findings:
----------------------------------------
  Unanimous (all models): ['SQL injection', 'parameterized']
  Consensus (majority):   ['SQL injection', 'parameterized']
  Any model found:        ['SQL injection', 'parameterized']
```

## Step 5: Use More Models

For comprehensive benchmarking, use all 13 models:

```python
from review_eval import BENCHMARK_MODELS

evaluator = MultiModelEvaluator(
    prompt_context="Review this code.",
    models=BENCHMARK_MODELS,
)

result = evaluator.evaluate(test_case)
print(f"Queried {result.total_models} models")
print(f"Pass Rate: {result.pass_rate:.0%}")
```

## Step 6: Async Evaluation

For better performance, use the async API:

```python
import asyncio

async def main():
    evaluator = MultiModelEvaluator(
        prompt_context="Review this code.",
        models=DEFAULT_MODELS,
    )

    # Async evaluation
    result = await evaluator.evaluate_async(test_case)
    print(f"Pass Rate: {result.pass_rate:.0%}")

asyncio.run(main())
```

## Model Tiers

DEFAULT_MODELS includes 3 frontier models:

| Model | Provider |
|-------|----------|
| Claude Opus 4.5 | Anthropic |
| GPT-5.1 Codex | OpenAI |
| Gemini 3 Pro | Google |

BENCHMARK_MODELS includes 13 models across 4 tiers:

| Tier | Models |
|------|--------|
| Frontier | Claude Opus, GPT-5.1, Gemini 3 |
| Production | Claude Sonnet, GPT-4o, Gemini 2.5 |
| Fast | Claude Haiku, GPT-4o Mini, Gemini Flash |
| Alternative | DeepSeek, Llama, Qwen, Mistral |

See [Model Tiers](../reference/model-tiers.md) for details.

## Choosing Consensus Level

### For Blocking PRs

Use unanimous agreement:

```python
if len(result.unanimous_issues) > 0:
    print("High-confidence issues found - consider blocking")
```

### For Review Comments

Use majority consensus:

```python
for issue in result.consensus_issues:
    post_comment(f"Potential issue: {issue}")
```

### For Security Audits

Use any-model for maximum sensitivity:

```python
for issue in result.any_model_issues:
    log_for_review(issue)
```

## Cost Considerations

More models = higher costs:

| Configuration | Est. Cost/Review |
|---------------|-----------------|
| DEFAULT_MODELS (3) | ~$0.03 |
| BENCHMARK_MODELS (13) | ~$0.10 |

Use DEFAULT_MODELS for most reviews, BENCHMARK_MODELS for critical paths.

## Next Steps

- [Integrate with GitHub Actions](github-actions-integration.md)
- [Configure custom models](../how-to/configure-models.md)
- [Understand how consensus works](../explanation/multi-model-consensus.md)
