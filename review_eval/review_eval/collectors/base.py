"""Base class for metric collectors."""

from abc import ABC, abstractmethod

from review_eval.models import MetricCategory, ScoringResult


class MetricCollector(ABC):
    """Abstract base class for collecting and normalizing PR metrics.

    Each collector is responsible for:
    1. Collecting raw metric data from a source (file, API, etc.)
    2. Normalizing the raw value to a 0-100 score
    3. Returning a ScoringResult with details

    Attributes:
        category: The metric category this collector handles.
        weight: Weight for this metric in final score calculation.
    """

    def __init__(self, category: MetricCategory, weight: float = 1.0):
        """Initialize the collector.

        Args:
            category: The metric category.
            weight: Weight for this metric (0.0-1.0).
        """
        self.category = category
        self.weight = weight

    @abstractmethod
    async def collect(self) -> ScoringResult:
        """Collect the metric and return normalized result.

        Returns:
            ScoringResult with raw value, normalized score, and details.

        Raises:
            Exception: If metric collection fails.
        """
        pass

    def _normalize(self, raw_value: float, details: dict) -> float:
        """Normalize raw metric value to 0-100 score.

        Default implementation returns raw_value as-is.
        Subclasses should override with custom normalization logic.

        Args:
            raw_value: The raw metric value.
            details: Additional context for normalization.

        Returns:
            Normalized score (0-100).
        """
        return max(0.0, min(100.0, raw_value))

    def _create_result(
        self, raw_value: float, normalized_score: float, details: dict, error: str | None = None
    ) -> ScoringResult:
        """Create a ScoringResult.

        Args:
            raw_value: The raw metric value.
            normalized_score: The normalized score (0-100).
            details: Additional details about the metric.
            error: Optional error message if collection failed.

        Returns:
            ScoringResult instance.
        """
        return ScoringResult(
            category=self.category,
            raw_value=raw_value,
            normalized_score=normalized_score,
            weight=self.weight,
            details=details,
            error_message=error,
        )
