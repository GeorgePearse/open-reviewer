"""Coverage collector - parses Cobertura XML from coverage.py."""

import math
import xml.etree.ElementTree as ET
from pathlib import Path

from review_eval.collectors.base import MetricCollector
from review_eval.models import MetricCategory, ScoringResult


class CoverageCollector(MetricCollector):
    """Collects coverage data from Cobertura XML files.

    Parses coverage.py Cobertura XML output to calculate coverage delta.
    Uses sigmoid mapping to normalize coverage changes to 0-100 score.

    Attributes:
        coverage_path: Path to Cobertura XML file.
        baseline_coverage: Baseline coverage percentage for delta calculation.
        tolerance: Ignore coverage changes smaller than this (e.g., 0.1%).
    """

    def __init__(
        self,
        coverage_path: Path,
        baseline_coverage: float | None = None,
        tolerance: float = 0.1,
        weight: float = 0.20,
    ):
        """Initialize the coverage collector.

        Args:
            coverage_path: Path to Cobertura XML file (e.g., coverage.xml).
            baseline_coverage: Baseline coverage % for delta calculation (if None, uses current as baseline).
            tolerance: Ignore deltas smaller than this percentage (default 0.1%).
            weight: Weight for this metric (default 0.20 = 20%).
        """
        super().__init__(MetricCategory.COVERAGE, weight)
        self.coverage_path = coverage_path
        self.baseline_coverage = baseline_coverage
        self.tolerance = tolerance

    async def collect(self) -> ScoringResult:
        """Parse Cobertura XML and calculate coverage delta.

        Returns:
            ScoringResult with coverage delta normalized to score.
        """
        try:
            if not self.coverage_path.exists():
                return self._create_result(
                    raw_value=0.0,
                    normalized_score=50.0,  # Neutral score if no coverage data
                    details={"error": "Coverage XML file not found"},
                    error=f"File not found: {self.coverage_path}",
                )

            # Parse Cobertura XML
            tree = ET.parse(self.coverage_path)
            root = tree.getroot()

            # Extract coverage percentage
            # Cobertura format: <coverage line-rate="0.85" branch-rate="0.75" ...>
            line_rate = float(root.get("line-rate", 0.0))
            branch_rate = float(root.get("branch-rate", 0.0))

            # Calculate overall coverage percentage
            current_coverage = line_rate * 100  # Convert to percentage

            # Calculate delta
            if self.baseline_coverage is None:
                # No baseline provided - use current as perfect score
                delta = 0.0
                baseline = current_coverage
            else:
                delta = current_coverage - self.baseline_coverage
                baseline = self.baseline_coverage

            # Apply tolerance threshold
            if abs(delta) < self.tolerance:
                delta = 0.0  # Ignore small changes

            # Normalize delta to score using sigmoid mapping
            # Delta of 0% = 50 points
            # Delta of +5% = 100 points
            # Delta of -5% = 0 points
            normalized_score = self._normalize_delta(delta)

            details = {
                "current_coverage": f"{current_coverage:.2f}%",
                "baseline_coverage": f"{baseline:.2f}%",
                "delta": f"{delta:+.2f}%",
                "line_rate": f"{line_rate:.2f}",
                "branch_rate": f"{branch_rate:.2f}",
                "tolerance": f"{self.tolerance}%",
            }

            return self._create_result(
                raw_value=delta, normalized_score=normalized_score, details=details
            )

        except ET.ParseError as e:
            return self._create_result(
                raw_value=0.0,
                normalized_score=50.0,
                details={"error": f"XML parse error: {e}"},
                error=f"Failed to parse Cobertura XML: {e}",
            )
        except Exception as e:
            return self._create_result(
                raw_value=0.0,
                normalized_score=50.0,
                details={"error": str(e)},
                error=f"Unexpected error collecting coverage: {e}",
            )

    def _normalize_delta(self, delta: float) -> float:
        """Normalize coverage delta to 0-100 score using sigmoid mapping.

        Args:
            delta: Coverage delta in percentage points (e.g., -2.5 or +3.0).

        Returns:
            Normalized score (0-100).
        """
        # Sigmoid mapping:
        # delta = 0  → score = 50
        # delta = +5 → score = 100
        # delta = -5 → score = 0

        # Use a sigmoid function: score = 50 + 50 * tanh(delta / 2)
        # This gives a smooth curve centered at 0 with range [0, 100]
        score = 50 + 50 * math.tanh(delta / 2.5)

        return max(0.0, min(100.0, score))
