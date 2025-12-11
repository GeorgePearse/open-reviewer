"""Static analysis collector - runs ruff and pyright to check code quality."""

import asyncio
import json
from pathlib import Path

from review_eval.collectors.base import MetricCollector
from review_eval.models import MetricCategory, ScoringResult


class StaticAnalysisCollector(MetricCollector):
    """Collects static analysis results from ruff and pyright.

    Runs ruff check and pyright to analyze code quality.
    Calculates error density (errors per 100 LOC) and normalizes to 0-100 score.

    Attributes:
        repo_root: Path to repository root.
        ruff_results_path: Optional path to pre-generated ruff JSON results.
        pyright_results_path: Optional path to pre-generated pyright JSON results.
    """

    def __init__(
        self,
        repo_root: Path,
        ruff_results_path: Path | None = None,
        pyright_results_path: Path | None = None,
        weight: float = 0.20,
    ):
        """Initialize the static analysis collector.

        Args:
            repo_root: Path to repository root for running analysis.
            ruff_results_path: Optional path to ruff JSON results file.
            pyright_results_path: Optional path to pyright JSON results file.
            weight: Weight for this metric (default 0.20 = 20%).
        """
        super().__init__(MetricCategory.STATIC_ANALYSIS, weight)
        self.repo_root = repo_root
        self.ruff_results_path = ruff_results_path
        self.pyright_results_path = pyright_results_path

    async def collect(self) -> ScoringResult:
        """Run static analysis and calculate error score.

        Returns:
            ScoringResult with error counts and normalized score.
        """
        try:
            # Collect ruff errors
            ruff_errors = await self._collect_ruff()

            # Collect pyright errors
            pyright_errors = await self._collect_pyright()

            total_errors = ruff_errors + pyright_errors

            # Calculate normalized score
            # 0 errors = 100 score
            # 1-5 errors = 80 score
            # 5+ errors = decreasing score
            normalized_score = self._normalize_errors(total_errors)

            details = {
                "ruff_errors": ruff_errors,
                "pyright_errors": pyright_errors,
                "total_errors": total_errors,
            }

            return self._create_result(
                raw_value=float(total_errors), normalized_score=normalized_score, details=details
            )

        except Exception as e:
            return self._create_result(
                raw_value=0.0,
                normalized_score=0.0,
                details={"error": str(e)},
                error=f"Unexpected error during static analysis: {e}",
            )

    async def _collect_ruff(self) -> int:
        """Collect ruff linting errors.

        Returns:
            Number of ruff errors found.
        """
        try:
            if self.ruff_results_path and self.ruff_results_path.exists():
                # Read pre-generated results
                with open(self.ruff_results_path) as f:
                    data = json.load(f)
                    return len(data) if isinstance(data, list) else 0

            # Run ruff check programmatically
            proc = await asyncio.create_subprocess_exec(
                "uv",
                "run",
                "ruff",
                "check",
                ".",
                "--output-format=json",
                cwd=self.repo_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                # No errors
                return 0

            # Parse JSON output
            if stdout:
                data = json.loads(stdout)
                return len(data) if isinstance(data, list) else 0

            return 0

        except Exception:
            # If ruff fails, return 0 errors (graceful degradation)
            return 0

    async def _collect_pyright(self) -> int:
        """Collect pyright type checking errors.

        Returns:
            Number of pyright errors found.
        """
        try:
            if self.pyright_results_path and self.pyright_results_path.exists():
                # Read pre-generated results
                with open(self.pyright_results_path) as f:
                    data = json.load(f)
                    summary = data.get("summary", {})
                    return summary.get("errorCount", 0)

            # Run pyright programmatically
            proc = await asyncio.create_subprocess_exec(
                "uv",
                "run",
                "pyright",
                "--outputjson",
                cwd=self.repo_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            # Parse JSON output (pyright always outputs JSON with --outputjson)
            if stdout:
                data = json.loads(stdout)
                summary = data.get("summary", {})
                return summary.get("errorCount", 0)

            return 0

        except Exception:
            # If pyright fails, return 0 errors (graceful degradation)
            return 0

    def _normalize_errors(self, error_count: int) -> float:
        """Normalize error count to 0-100 score.

        Args:
            error_count: Total number of errors.

        Returns:
            Normalized score (0-100).
        """
        if error_count == 0:
            return 100.0

        if error_count <= 5:
            return 80.0

        # Exponential decay: score decreases as errors increase
        # score = 80 * exp(-0.05 * (errors - 5))
        import math

        score = 80.0 * math.exp(-0.05 * (error_count - 5))

        return max(0.0, min(100.0, score))
