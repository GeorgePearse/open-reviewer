"""Multi-model evaluation using OpenRouter for consensus-based code review."""

import asyncio
import os
import time
from collections import Counter

from openai import AsyncOpenAI

from review_eval.models import (
    GoldenTestCase,
    ModelConfig,
    ModelReviewResult,
    MultiModelResult,
)

# Primary models for production use
DEFAULT_MODELS: list[ModelConfig] = [
    ModelConfig(name="Claude Opus 4.5", model_id="anthropic/claude-opus-4.5", weight=1.0),
    ModelConfig(name="GPT-5.1 Codex", model_id="openai/gpt-5.1-codex", weight=1.0),
    ModelConfig(name="Gemini 3 Pro", model_id="google/gemini-3-pro-preview", weight=1.0),
]

# Extended model set for comprehensive benchmarking
BENCHMARK_MODELS: list[ModelConfig] = [
    # Tier 1: Frontier models
    ModelConfig(name="Claude Opus 4.5", model_id="anthropic/claude-opus-4.5", weight=1.0),
    ModelConfig(name="GPT-5.1 Codex", model_id="openai/gpt-5.1-codex", weight=1.0),
    ModelConfig(name="Gemini 3 Pro", model_id="google/gemini-3-pro-preview", weight=1.0),
    # Tier 2: Strong production models
    ModelConfig(name="Claude 3.5 Sonnet", model_id="anthropic/claude-3.5-sonnet", weight=0.9),
    ModelConfig(name="GPT-4o", model_id="openai/gpt-4o", weight=0.9),
    ModelConfig(name="Gemini 2.5 Pro", model_id="google/gemini-2.5-pro-preview-05-06", weight=0.9),
    # Tier 3: Fast/efficient models
    ModelConfig(name="Claude 3.5 Haiku", model_id="anthropic/claude-3.5-haiku", weight=0.7),
    ModelConfig(name="GPT-4o Mini", model_id="openai/gpt-4o-mini", weight=0.7),
    ModelConfig(name="Gemini 2.0 Flash", model_id="google/gemini-2.0-flash-001", weight=0.7),
    # Tier 4: Alternative providers
    ModelConfig(name="DeepSeek V3", model_id="deepseek/deepseek-chat", weight=0.8),
    ModelConfig(name="Llama 3.3 70B", model_id="meta-llama/llama-3.3-70b-instruct", weight=0.6),
    ModelConfig(name="Qwen 2.5 72B", model_id="qwen/qwen-2.5-72b-instruct", weight=0.6),
    ModelConfig(name="Mistral Large", model_id="mistralai/mistral-large-2411", weight=0.7),
]


class MultiModelEvaluator:
    """Evaluates code review quality using multiple models via OpenRouter.

    This class queries multiple LLMs in parallel and aggregates their findings
    to provide consensus-based evaluation of code review quality.

    Attributes:
        client: OpenRouter-compatible OpenAI client.
        models: List of models to query.
        prompt_context: System prompt for code review.
    """

    def __init__(
        self,
        prompt_context: str,
        models: list[ModelConfig] | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize the multi-model evaluator.

        Args:
            prompt_context: System prompt with review instructions.
            models: List of models to use (defaults to DEFAULT_MODELS).
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var).
        """
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY"),
        )
        self.models = models or DEFAULT_MODELS
        self.prompt_context = prompt_context

    async def _query_model(
        self,
        model: ModelConfig,
        code: str,
    ) -> tuple[str, float]:
        """Query a single model and return response with latency.

        Args:
            model: The model configuration to use.
            code: The code to review.

        Returns:
            Tuple of (response_text, latency_ms).
        """
        start = time.perf_counter()
        response = await self.client.chat.completions.create(
            model=model.model_id,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": self.prompt_context},
                {"role": "user", "content": f"Review this code for issues:\n\n```\n{code}\n```"},
            ],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        text = response.choices[0].message.content or ""
        return text, latency_ms

    async def _evaluate_single_model(
        self,
        model: ModelConfig,
        test_case: GoldenTestCase,
    ) -> ModelReviewResult:
        """Evaluate a test case with a single model.

        Args:
            model: The model to use.
            test_case: The test case to evaluate.

        Returns:
            ModelReviewResult with the model's findings.
        """
        try:
            review_text, latency_ms = await self._query_model(model, test_case.code)
            review_text_lower = review_text.lower()

            matched = [issue for issue in test_case.expected_issues if issue.lower() in review_text_lower]
            missed = [issue for issue in test_case.expected_issues if issue.lower() not in review_text_lower]

            return ModelReviewResult(
                model_name=model.name,
                model_id=model.model_id,
                review_text=review_text,
                matched_issues=matched,
                missed_issues=missed,
                passed=len(missed) == 0,
                latency_ms=latency_ms,
            )
        except Exception as e:
            return ModelReviewResult(
                model_name=model.name,
                model_id=model.model_id,
                review_text=f"Error: {e}",
                matched_issues=[],
                missed_issues=test_case.expected_issues,
                passed=False,
                latency_ms=0.0,
            )

    async def evaluate_async(self, test_case: GoldenTestCase) -> MultiModelResult:
        """Evaluate a test case with all models in parallel.

        Args:
            test_case: The test case to evaluate.

        Returns:
            MultiModelResult with aggregated findings from all models.
        """
        tasks = [self._evaluate_single_model(model, test_case) for model in self.models]
        results = await asyncio.gather(*tasks)

        # Aggregate findings
        all_matched: list[str] = []
        for result in results:
            all_matched.extend(result.matched_issues)

        # Count how many models found each issue
        issue_counts = Counter(all_matched)
        total_models = len(self.models)
        majority_threshold = total_models // 2 + 1

        # Consensus: found by majority of models
        consensus_issues = [issue for issue, count in issue_counts.items() if count >= majority_threshold]

        # Unanimous: found by ALL models
        unanimous_issues = [issue for issue, count in issue_counts.items() if count == total_models]

        # Any: found by at least one model
        any_model_issues = list(issue_counts.keys())

        # Check if consensus caught all expected issues
        consensus_matched = set(consensus_issues)
        expected_set = {issue.lower() for issue in test_case.expected_issues}
        consensus_passed = expected_set.issubset({issue.lower() for issue in consensus_matched})

        models_passed = sum(1 for r in results if r.passed)

        return MultiModelResult(
            test_id=test_case.id,
            model_results=list(results),
            consensus_issues=consensus_issues,
            unanimous_issues=unanimous_issues,
            any_model_issues=any_model_issues,
            consensus_passed=consensus_passed,
            models_passed=models_passed,
            total_models=total_models,
        )

    def evaluate(self, test_case: GoldenTestCase) -> MultiModelResult:
        """Synchronous wrapper for evaluate_async.

        Args:
            test_case: The test case to evaluate.

        Returns:
            MultiModelResult with aggregated findings.
        """
        return asyncio.run(self.evaluate_async(test_case))


def print_multi_model_report(result: MultiModelResult) -> None:
    """Print a formatted report of multi-model evaluation results.

    Args:
        result: The multi-model result to display.
    """
    print(f"\n{'=' * 60}")
    print(f"Test: {result.test_id}")
    print(f"{'=' * 60}")
    print(f"Pass Rate: {result.models_passed}/{result.total_models} ({result.pass_rate:.0%})")
    print(f"Consensus Passed: {'✓' if result.consensus_passed else '✗'}")
    print()

    print("Individual Model Results:")
    print("-" * 40)
    for mr in result.model_results:
        status = "✓" if mr.passed else "✗"
        print(f"  {status} {mr.model_name} ({mr.latency_ms:.0f}ms)")
        if mr.matched_issues:
            print(f"     Caught: {', '.join(mr.matched_issues)}")
        if mr.missed_issues:
            print(f"     Missed: {', '.join(mr.missed_issues)}")
    print()

    print("Aggregated Findings:")
    print("-" * 40)
    print(f"  Unanimous (all models): {result.unanimous_issues or 'None'}")
    print(f"  Consensus (majority):   {result.consensus_issues or 'None'}")
    print(f"  Any model found:        {result.any_model_issues or 'None'}")
