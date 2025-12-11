"""AI review collector - aggregates findings from multi-model code review."""

from pathlib import Path

from review_eval.collectors.base import MetricCollector
from review_eval.models import MetricCategory, MultiModelResult, ScoringResult


class AIReviewCollector(MetricCollector):
    """Collects AI code review findings from multi-model evaluations.

    Aggregates consensus issues from MultiModelEvaluator results.
    Calculates score based on issue severity distribution.

    Attributes:
        review_results: List of MultiModelResult from AI reviews.
        security_keywords: Keywords that indicate security issues.
    """

    def __init__(
        self,
        review_results: list[MultiModelResult] | None = None,
        review_results_path: Path | None = None,
        weight: float = 0.30,
    ):
        """Initialize the AI review collector.

        Args:
            review_results: List of MultiModelResult objects from reviews.
            review_results_path: Optional path to JSON file with review results.
            weight: Weight for this metric (default 0.30 = 30%).
        """
        super().__init__(MetricCategory.AI_REVIEW, weight)
        self.review_results = review_results or []
        self.review_results_path = review_results_path

        # Keywords that indicate security issues
        self.security_keywords = [
            "injection",
            "security",
            "vulnerability",
            "xss",
            "csrf",
            "secret",
            "credential",
            "authentication",
            "authorization",
            "sql injection",
            "command injection",
            "hardcoded",
        ]

    async def collect(self) -> ScoringResult:
        """Aggregate AI review findings and calculate score.

        Returns:
            ScoringResult with issue counts and normalized score.
        """
        try:
            # Load results from file if provided
            if self.review_results_path and self.review_results_path.exists():
                import json

                with open(self.review_results_path) as f:
                    data = json.load(f)
                    # Convert JSON to MultiModelResult objects
                    self.review_results = [
                        MultiModelResult(**result) for result in data if isinstance(result, dict)
                    ]

            if not self.review_results:
                # No review results available - return neutral score
                return self._create_result(
                    raw_value=0.0,
                    normalized_score=100.0,  # No issues found = perfect score
                    details={
                        "total_reviews": 0,
                        "warning": "No AI review results available",
                    },
                )

            # Aggregate consensus issues across all reviews
            all_consensus_issues: list[str] = []
            for result in self.review_results:
                all_consensus_issues.extend(result.consensus_issues)

            # Categorize issues by severity
            security_issues = 0
            high_issues = 0
            medium_issues = 0
            low_issues = 0

            for issue in all_consensus_issues:
                issue_lower = issue.lower()

                # Check for security issues
                if any(keyword in issue_lower for keyword in self.security_keywords):
                    security_issues += 1
                elif any(
                    severity in issue_lower
                    for severity in ["critical", "severe", "dangerous", "unsafe"]
                ):
                    high_issues += 1
                elif any(
                    severity in issue_lower for severity in ["warning", "caution", "consider"]
                ):
                    medium_issues += 1
                else:
                    low_issues += 1

            # Calculate normalized score
            # Formula: 100 - (critical * 50) - (high * 20) - (medium * 5) - (low * 1)
            deductions = (
                security_issues * 50 + high_issues * 20 + medium_issues * 5 + low_issues * 1
            )
            normalized_score = max(0.0, 100.0 - deductions)

            details = {
                "total_reviews": len(self.review_results),
                "total_consensus_issues": len(all_consensus_issues),
                "security_issues": security_issues,
                "high_severity": high_issues,
                "medium_severity": medium_issues,
                "low_severity": low_issues,
                "consensus_issues": all_consensus_issues[:10],  # Include first 10 for reference
            }

            return self._create_result(
                raw_value=float(len(all_consensus_issues)),
                normalized_score=normalized_score,
                details=details,
            )

        except Exception as e:
            return self._create_result(
                raw_value=0.0,
                normalized_score=50.0,  # Neutral score on error
                details={"error": str(e)},
                error=f"Unexpected error collecting AI review results: {e}",
            )
