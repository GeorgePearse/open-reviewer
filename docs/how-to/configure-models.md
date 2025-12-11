# Configure Models

Customize which AI models Open Reviewer uses for evaluations.

## Use Default Models

The simplest configuration:

```python
from review_eval import MultiModelEvaluator, DEFAULT_MODELS

evaluator = MultiModelEvaluator(
    prompt_context="Review this code.",
    models=DEFAULT_MODELS,
)
```

DEFAULT_MODELS includes Claude Opus 4.5, GPT-5.1 Codex, and Gemini 3 Pro.

## Use All Benchmark Models

For comprehensive analysis:

```python
from review_eval import MultiModelEvaluator, BENCHMARK_MODELS

evaluator = MultiModelEvaluator(
    prompt_context="Review this code.",
    models=BENCHMARK_MODELS,  # 13 models
)
```

## Create Custom Model Lists

### Select Specific Models

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
        weight=1.0,
    ),
]

evaluator = MultiModelEvaluator(
    prompt_context="Review this code.",
    models=my_models,
)
```

### Use Fast Models Only

```python
fast_models = [
    ModelConfig(name="Claude Haiku", model_id="anthropic/claude-3.5-haiku"),
    ModelConfig(name="GPT-4o Mini", model_id="openai/gpt-4o-mini"),
    ModelConfig(name="Gemini Flash", model_id="google/gemini-2.0-flash-001"),
]

evaluator = MultiModelEvaluator(
    prompt_context="Review this code.",
    models=fast_models,
)
```

### Mix Tiers

```python
mixed_models = [
    # One frontier for accuracy
    ModelConfig(name="Claude Opus", model_id="anthropic/claude-opus-4.5", weight=1.0),
    # Two fast for speed/cost
    ModelConfig(name="GPT Mini", model_id="openai/gpt-4o-mini", weight=0.7),
    ModelConfig(name="Gemini Flash", model_id="google/gemini-2.0-flash-001", weight=0.7),
]
```

## Configure Model Weights

Weights can be used for custom consensus logic:

```python
ModelConfig(
    name="Claude Opus",
    model_id="anthropic/claude-opus-4.5",
    weight=1.0,   # Full weight (most trusted)
)

ModelConfig(
    name="Llama 70B",
    model_id="meta-llama/llama-3.3-70b-instruct",
    weight=0.6,   # Lower weight (less trusted)
)
```

!!! note
    Currently weights are stored but not used in consensus calculation.
    Majority voting uses simple counting.

## Available Models

See [Model Tiers](../reference/model-tiers.md) for the complete list.

### Finding Model IDs

Model IDs follow the format `provider/model-name`:

- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4o`
- `google/gemini-2.5-pro-preview-05-06`

Check [OpenRouter Models](https://openrouter.ai/models) for available models.

## Environment-Based Configuration

Load models from environment:

```python
import os
import json
from review_eval import ModelConfig, MultiModelEvaluator

# Set via environment
# REVIEW_MODELS='[{"name":"Claude","model_id":"anthropic/claude-3.5-sonnet"}]'

models_json = os.environ.get("REVIEW_MODELS")
if models_json:
    models_data = json.loads(models_json)
    models = [ModelConfig(**m) for m in models_data]
else:
    models = DEFAULT_MODELS

evaluator = MultiModelEvaluator(prompt_context="...", models=models)
```

## Configuration by Use Case

### Development (Fast Feedback)

```python
dev_models = [
    ModelConfig(name="GPT-4o Mini", model_id="openai/gpt-4o-mini"),
]
```

### CI/CD (Balanced)

```python
ci_models = [
    ModelConfig(name="Claude Sonnet", model_id="anthropic/claude-3.5-sonnet"),
    ModelConfig(name="GPT-4o", model_id="openai/gpt-4o"),
]
```

### Security Audit (Comprehensive)

```python
from review_eval import BENCHMARK_MODELS
audit_models = BENCHMARK_MODELS  # All 13 models
```

## Troubleshooting

### Model Not Found

Verify the model ID on [OpenRouter](https://openrouter.ai/models).

### Rate Limits

Reduce parallel models or add delays:

```python
evaluator = MultiModelEvaluator(
    prompt_context="...",
    models=my_models[:3],  # Use fewer models
)
```

### High Costs

Use cheaper models for development:

```python
# ~$0.01/review vs ~$0.10/review
cheap_models = [
    ModelConfig(name="GPT-4o Mini", model_id="openai/gpt-4o-mini"),
]
```
