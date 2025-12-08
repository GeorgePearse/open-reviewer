"""PR Scoring Engine - orchestrates metric collection and score calculation."""

import asyncio
from pathlib import Path
from typing import Literal

from review_eval.collectors.base import MetricCollector
from review_eval.models import MetricCategory, PRScore, ScoringConfig, ScoringResult


class ScoringEngine:
    """Orchestrates metric collection and PR score calculation.

    Uses the Hybrid Deduction Model:
        Score = Σ(CategoryScore × Weight) - CriticalPenalties

    Attributes:
        config: Scoring configuration (thresholds, weights, penalties).
        collectors: List of metric collectors to run.
    """

    def __init__(self, config: ScoringConfig, collectors: list[MetricCollector]):
        """Initialize the scoring engine.

        Args:
            config: Scoring configuration.
            collectors: List of metric collectors.
        """
        self.config = config
        self.collectors = collectors

        # Validate configuration
        if not self.config.validate_weights():
            raise ValueError(
                f"Weights must sum to 1.0, got {sum(self.config.weights.values()):.2f}"
            )

    async def calculate_score(self) -> PRScore:
        """Calculate PR score by running all collectors.

        Returns:
            PRScore with final score, status, and breakdown.
        """
        # Run all collectors in parallel
        results = await asyncio.gather(*[collector.collect() for collector in self.collectors])

        # Build breakdown dict
        breakdown: dict[MetricCategory, ScoringResult] = {}
        for result in results:
            breakdown[result.category] = result

        # Calculate weighted sum
        weighted_score = 0.0
        for category, result in breakdown.items():
            weight = self.config.weights.get(category, 0.0)
            weighted_score += result.normalized_score * weight

        # Apply critical penalties
        blocking_factors: list[str] = []
        penalties = 0.0

        # Check for critical issues in breakdown
        for category, result in breakdown.items():
            if result.error_message:
                # Collection failure is not a blocker, just reduces score for that category
                continue

            # Check for security vulnerabilities (AI Review)
            if category == MetricCategory.AI_REVIEW:
                security_count = result.details.get("security_issues", 0)
                if security_count > 0:
                    penalty = self.config.critical_penalties.get("security_vulnerability", 0)
                    penalties += penalty
                    blocking_factors.append(
                        f"Security vulnerability detected ({security_count} issue(s))"
                    )

            # Check for critical test failures
            if category == MetricCategory.TESTS:
                failed_count = result.details.get("failed", 0)
                total_count = result.details.get("total", 0)
                if total_count > 0 and failed_count == total_count:
                    # All tests failing
                    penalty = self.config.critical_penalties.get("critical_test_failure", 0)
                    penalties += penalty
                    blocking_factors.append(f"All tests failing ({failed_count}/{total_count})")

        # Calculate final score
        final_score = max(0.0, weighted_score - penalties)
        final_score = min(100.0, final_score)  # Clamp to [0, 100]

        # Determine pass/fail status
        status: Literal["PASS", "FAIL"] = (
            "PASS" if final_score >= self.config.threshold and not blocking_factors else "FAIL"
        )

        return PRScore(
            total_score=final_score,
            status=status,
            threshold=self.config.threshold,
            blocking_factors=blocking_factors,
            breakdown=breakdown,
        )

    @classmethod
    def from_config_file(
        cls, config_path: Path, collectors: list[MetricCollector]
    ) -> "ScoringEngine":
        """Create a ScoringEngine from a YAML config file.

        Args:
            config_path: Path to reviewer.yaml configuration.
            collectors: List of metric collectors.

        Returns:
            ScoringEngine instance.
        """
        import yaml

        with open(config_path) as f:
            data = yaml.safe_load(f)

        scoring_data = data.get("scoring", {})

        # Parse config
        config = ScoringConfig(
            threshold=scoring_data.get("threshold", 80.0),
            weights={
                MetricCategory.TESTS: scoring_data.get("weights", {}).get("tests", 0.30),
                MetricCategory.COVERAGE: scoring_data.get("weights", {}).get("coverage", 0.20),
                MetricCategory.STATIC_ANALYSIS: scoring_data.get("weights", {}).get(
                    "static_analysis", 0.20
                ),
                MetricCategory.AI_REVIEW: scoring_data.get("weights", {}).get("ai_review", 0.30),
            },
            critical_penalties=scoring_data.get(
                "critical_penalties",
                {
                    "security_vulnerability": 100.0,
                    "critical_test_failure": 50.0,
                },
            ),
            tolerance=scoring_data.get(
                "tolerance",
                {
                    "coverage_delta": 0.1,
                },
            ),
        )

        return cls(config, collectors)
