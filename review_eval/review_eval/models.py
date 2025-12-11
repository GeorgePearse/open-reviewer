"""Pydantic models for review evaluation."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for a model to use in evaluation.

    Attributes:
        name: Human-readable name for the model.
        model_id: The model identifier (e.g., 'anthropic/claude-3.5-sonnet').
        provider: The provider ('openrouter', 'anthropic', 'openai').
        weight: Weight for consensus scoring (default 1.0).
    """

    name: str
    model_id: str
    provider: str = "openrouter"
    weight: float = 1.0


class ModelReviewResult(BaseModel):
    """Result from a single model's review.

    Attributes:
        model_name: Name of the model that produced this review.
        model_id: Full model identifier.
        review_text: The model's review response.
        matched_issues: Issues correctly identified.
        missed_issues: Issues the model failed to catch.
        passed: Whether all expected issues were found.
        latency_ms: Response time in milliseconds.
    """

    model_name: str
    model_id: str
    review_text: str
    matched_issues: list[str]
    missed_issues: list[str]
    passed: bool
    latency_ms: float = 0.0


class MultiModelResult(BaseModel):
    """Aggregated result from multiple models reviewing the same code.

    Attributes:
        test_id: ID of the test case evaluated.
        model_results: Individual results from each model.
        consensus_issues: Issues found by majority of models.
        unanimous_issues: Issues found by ALL models.
        any_model_issues: Issues found by at least one model.
        consensus_passed: Whether consensus caught all expected issues.
        models_passed: Number of models that passed individually.
        total_models: Total number of models queried.
    """

    test_id: str
    model_results: list[ModelReviewResult]
    consensus_issues: list[str]
    unanimous_issues: list[str]
    any_model_issues: list[str]
    consensus_passed: bool
    models_passed: int
    total_models: int

    @property
    def pass_rate(self) -> float:
        """Percentage of models that passed."""
        return self.models_passed / self.total_models if self.total_models > 0 else 0.0


class GoldenTestCase(BaseModel):
    """A test case with known-bad code and expected findings.

    Attributes:
        id: Unique identifier for the test case.
        file_path: Path to the fixture file (for reference).
        code: The code snippet to review.
        expected_issues: Keywords that MUST appear in the review response.
        severity: Expected severity level of the issues.
        category: Category of anti-pattern (python, typescript, sql, security).
    """

    id: str
    file_path: str
    code: str
    expected_issues: list[str] = Field(
        description="Keywords that MUST appear in review (e.g., 'psycopg2', 'type annotation')"
    )
    severity: str = "high"
    category: str


class ReviewResult(BaseModel):
    """Result from Claude review evaluation.

    Attributes:
        test_id: ID of the test case that was evaluated.
        passed: Whether all expected issues were found.
        review_text: Full text of Claude's review response.
        matched_issues: Issues that were correctly identified.
        missed_issues: Issues that Claude failed to catch.
    """

    test_id: str
    passed: bool
    review_text: str
    matched_issues: list[str]
    missed_issues: list[str]


# ============================================================================
# PR Scoring Models
# ============================================================================


class MetricCategory(StrEnum):
    """Categories of metrics for PR scoring."""

    TESTS = "tests"
    COVERAGE = "coverage"
    STATIC_ANALYSIS = "static_analysis"
    AI_REVIEW = "ai_review"


class ScoringResult(BaseModel):
    """Result from a single metric collector.

    Attributes:
        category: The metric category this result represents.
        raw_value: The raw metric value before normalization.
        normalized_score: Score normalized to 0-100 scale.
        weight: Weight applied to this metric in final score.
        details: Additional details about the metric collection.
        error_message: Error message if metric collection failed.
    """

    category: MetricCategory
    raw_value: float
    normalized_score: float  # 0-100
    weight: float
    details: dict[str, Any]
    error_message: str | None = None


class PRScore(BaseModel):
    """Final PR score with breakdown.

    Attributes:
        total_score: Final aggregated score (0-100).
        status: Whether the PR passed the quality gate.
        threshold: Minimum score required to pass.
        blocking_factors: List of critical issues that caused failure.
        breakdown: Individual metric scores by category.
        timestamp: When the score was calculated.
    """

    total_score: float  # 0-100
    status: Literal["PASS", "FAIL"]
    threshold: float
    blocking_factors: list[str]
    breakdown: dict[MetricCategory, ScoringResult]
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ScoringConfig(BaseModel):
    """Configuration for PR scoring.

    Attributes:
        threshold: Minimum score required to pass (0-100).
        weights: Weight for each metric category (must sum to 1.0).
        critical_penalties: Point deductions for critical issues.
        tolerance: Tolerance thresholds for noisy metrics.
    """

    threshold: float = 80.0  # Minimum passing score
    weights: dict[MetricCategory, float] = Field(
        default_factory=lambda: {
            MetricCategory.TESTS: 0.30,
            MetricCategory.COVERAGE: 0.20,
            MetricCategory.STATIC_ANALYSIS: 0.20,
            MetricCategory.AI_REVIEW: 0.30,
        }
    )
    critical_penalties: dict[str, float] = Field(
        default_factory=lambda: {
            "security_vulnerability": 100.0,  # Immediate fail
            "critical_test_failure": 50.0,
        }
    )
    tolerance: dict[str, float] = Field(
        default_factory=lambda: {
            "coverage_delta": 0.1,  # Ignore drops < 0.1%
        }
    )

    def validate_weights(self) -> bool:
        """Validate that weights sum to approximately 1.0."""
        total = sum(self.weights.values())
        return abs(total - 1.0) < 0.01  # Allow small floating point error
