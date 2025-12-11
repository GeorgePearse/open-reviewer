"""Test result collector - parses JUnit XML from pytest."""

import xml.etree.ElementTree as ET
from pathlib import Path

from review_eval.collectors.base import MetricCollector
from review_eval.models import MetricCategory, ScoringResult


class TestResultCollector(MetricCollector):
    """Collects test results from JUnit XML files.

    Parses pytest JUnit XML output to calculate test pass rate.
    Normalizes to 0-100 score based on percentage of tests passing.

    Attributes:
        junit_path: Path to JUnit XML file.
    """

    def __init__(self, junit_path: Path, weight: float = 0.30):
        """Initialize the test result collector.

        Args:
            junit_path: Path to JUnit XML file (e.g., junit.xml).
            weight: Weight for this metric (default 0.30 = 30%).
        """
        super().__init__(MetricCategory.TESTS, weight)
        self.junit_path = junit_path

    async def collect(self) -> ScoringResult:
        """Parse JUnit XML and calculate test pass rate.

        Returns:
            ScoringResult with test pass rate as score.
        """
        try:
            if not self.junit_path.exists():
                return self._create_result(
                    raw_value=0.0,
                    normalized_score=0.0,
                    details={"error": "JUnit XML file not found"},
                    error=f"File not found: {self.junit_path}",
                )

            # Parse JUnit XML
            tree = ET.parse(self.junit_path)
            root = tree.getroot()

            # Extract test counts
            # JUnit XML format: <testsuites><testsuite tests="X" failures="Y" errors="Z" skipped="W">
            total = 0
            failed = 0
            errors = 0
            skipped = 0

            # Handle both <testsuites> and <testsuite> root elements
            if root.tag == "testsuites":
                for testsuite in root.findall("testsuite"):
                    total += int(testsuite.get("tests", 0))
                    failed += int(testsuite.get("failures", 0))
                    errors += int(testsuite.get("errors", 0))
                    skipped += int(testsuite.get("skipped", 0))
            elif root.tag == "testsuite":
                total = int(root.get("tests", 0))
                failed = int(root.get("failures", 0))
                errors = int(root.get("errors", 0))
                skipped = int(root.get("skipped", 0))
            else:
                return self._create_result(
                    raw_value=0.0,
                    normalized_score=0.0,
                    details={"error": f"Unknown root element: {root.tag}"},
                    error=f"Invalid JUnit XML: unknown root element {root.tag}",
                )

            # Calculate pass rate
            if total == 0:
                # No tests found
                return self._create_result(
                    raw_value=0.0,
                    normalized_score=0.0,
                    details={
                        "total": 0,
                        "passed": 0,
                        "failed": 0,
                        "errors": 0,
                        "skipped": skipped,
                        "warning": "No tests found",
                    },
                    error="No tests found in JUnit XML",
                )

            passed = total - failed - errors
            pass_rate = (passed / total) * 100

            details = {
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
                "pass_rate": f"{pass_rate:.1f}%",
            }

            # Normalize: pass_rate is already 0-100
            normalized_score = pass_rate

            return self._create_result(
                raw_value=pass_rate, normalized_score=normalized_score, details=details
            )

        except ET.ParseError as e:
            return self._create_result(
                raw_value=0.0,
                normalized_score=0.0,
                details={"error": f"XML parse error: {e}"},
                error=f"Failed to parse JUnit XML: {e}",
            )
        except Exception as e:
            return self._create_result(
                raw_value=0.0,
                normalized_score=0.0,
                details={"error": str(e)},
                error=f"Unexpected error collecting test results: {e}",
            )
