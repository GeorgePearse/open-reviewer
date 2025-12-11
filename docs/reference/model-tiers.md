# Model Tiers

Open Reviewer supports 13 models across 4 tiers via OpenRouter.

## Tier Overview

| Tier | Models | Weight | Use Case |
|------|--------|--------|----------|
| **Frontier** | 3 | 1.0 | Highest accuracy, production critical |
| **Production** | 3 | 0.9 | Daily production use |
| **Fast** | 3 | 0.7 | Quick iteration, cost-sensitive |
| **Alternative** | 4 | 0.6-0.8 | Diversity, specific strengths |

## DEFAULT_MODELS

The default configuration uses three frontier models:

```python
from review_eval import DEFAULT_MODELS

# DEFAULT_MODELS contains:
# - Claude Opus 4.5
# - GPT-5.1 Codex
# - Gemini 3 Pro
```

## BENCHMARK_MODELS

For comprehensive benchmarking, use all 13 models:

```python
from review_eval import BENCHMARK_MODELS, MultiModelEvaluator

evaluator = MultiModelEvaluator(
    prompt_context="Review this code.",
    models=BENCHMARK_MODELS,
)
```

## Complete Model List

### Tier 1: Frontier

Top-tier models for maximum accuracy.

| Model | ID | Weight |
|-------|---|--------|
| Claude Opus 4.5 | `anthropic/claude-opus-4.5` | 1.0 |
| GPT-5.1 Codex | `openai/gpt-5.1-codex` | 1.0 |
| Gemini 3 Pro | `google/gemini-3-pro-preview` | 1.0 |

### Tier 2: Production

Strong models for daily production use.

| Model | ID | Weight |
|-------|---|--------|
| Claude 3.5 Sonnet | `anthropic/claude-3.5-sonnet` | 0.9 |
| GPT-4o | `openai/gpt-4o` | 0.9 |
| Gemini 2.5 Pro | `google/gemini-2.5-pro-preview-05-06` | 0.9 |

### Tier 3: Fast

Quick, cost-effective models.

| Model | ID | Weight |
|-------|---|--------|
| Claude 3.5 Haiku | `anthropic/claude-3.5-haiku` | 0.7 |
| GPT-4o Mini | `openai/gpt-4o-mini` | 0.7 |
| Gemini 2.0 Flash | `google/gemini-2.0-flash-001` | 0.7 |

### Tier 4: Alternative

Models from other providers for diversity.

| Model | ID | Weight |
|-------|---|--------|
| DeepSeek V3 | `deepseek/deepseek-chat` | 0.8 |
| Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct` | 0.6 |
| Qwen 2.5 72B | `qwen/qwen-2.5-72b-instruct` | 0.6 |
| Mistral Large | `mistralai/mistral-large-2411` | 0.7 |

## Custom Model Configuration

Create custom model configurations:

```python
from review_eval import ModelConfig, MultiModelEvaluator

my_models = [
    ModelConfig(
        name="Claude Sonnet",
        model_id="anthropic/claude-3.5-sonnet",
        weight=1.0,
    ),
    ModelConfig(
        name="GPT-4o",
        model_id="openai/gpt-4o",
        weight=0.9,
    ),
]

evaluator = MultiModelEvaluator(
    prompt_context="...",
    models=my_models,
)
```

## Weight System

Weights affect consensus scoring:

- **1.0** - Full weight in consensus calculations
- **0.9** - Slightly reduced influence
- **0.7** - Reduced influence (fast models)
- **0.6** - Lower confidence (open-source models)

!!! note "Consensus Calculation"
    Currently, weights are stored but not used in the majority voting.
    Consensus is calculated by simple majority: `count >= total // 2 + 1`

## Choosing Models

### For Production Reviews

Use `DEFAULT_MODELS` (3 frontier models):

```python
evaluator = MultiModelEvaluator(prompt, models=DEFAULT_MODELS)
```

### For Comprehensive Benchmarking

Use `BENCHMARK_MODELS` (all 13 models):

```python
evaluator = MultiModelEvaluator(prompt, models=BENCHMARK_MODELS)
```

### For Cost-Sensitive Workloads

Create a custom list with fast models:

```python
fast_models = [
    ModelConfig(name="Claude Haiku", model_id="anthropic/claude-3.5-haiku", weight=1.0),
    ModelConfig(name="GPT-4o Mini", model_id="openai/gpt-4o-mini", weight=1.0),
    ModelConfig(name="Gemini Flash", model_id="google/gemini-2.0-flash-001", weight=1.0),
]
```

### For Maximum Diversity

Include models from different providers:

```python
diverse_models = [
    ModelConfig(name="Claude", model_id="anthropic/claude-3.5-sonnet", weight=1.0),
    ModelConfig(name="GPT", model_id="openai/gpt-4o", weight=1.0),
    ModelConfig(name="Gemini", model_id="google/gemini-2.5-pro-preview-05-06", weight=1.0),
    ModelConfig(name="DeepSeek", model_id="deepseek/deepseek-chat", weight=1.0),
    ModelConfig(name="Llama", model_id="meta-llama/llama-3.3-70b-instruct", weight=1.0),
]
```
