"""Pydantic models for review evaluation."""

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
    expected_issues: list[str] = Field(description="Keywords that MUST appear in review (e.g., 'psycopg2', 'type annotation')")
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
