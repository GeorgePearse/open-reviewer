"""Tests for metric collectors."""

import tempfile
from pathlib import Path

import pytest

from review_eval.collectors import (
    AIReviewCollector,
    CoverageCollector,
    StaticAnalysisCollector,
    TestResultCollector,
)
from review_eval.models import MetricCategory, ModelReviewResult, MultiModelResult


@pytest.mark.asyncio
async def test_test_collector_perfect_pass_rate():
    """Test collector should return 100 for all passing tests."""
    junit_xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
    <testsuite name="pytest" tests="10" failures="0" errors="0" skipped="0">
        <testcase classname="test_example" name="test_1" time="0.001"/>
        <testcase classname="test_example" name="test_2" time="0.001"/>
    </testsuite>
</testsuites>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(junit_xml)
        junit_path = Path(f.name)

    try:
        collector = TestResultCollector(junit_path)
        result = await collector.collect()

        assert result.category == MetricCategory.TESTS
        assert result.normalized_score == 100.0
        assert result.details["total"] == 10
        assert result.details["passed"] == 10
        assert result.details["failed"] == 0
        assert result.error_message is None
    finally:
        junit_path.unlink()


@pytest.mark.asyncio
async def test_test_collector_partial_failures():
    """Test collector should calculate correct pass rate with failures."""
    junit_xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuite tests="10" failures="2" errors="1" skipped="0">
    <testcase classname="test_example" name="test_1" time="0.001"/>
    <testcase classname="test_example" name="test_2" time="0.001">
        <failure message="assertion failed"/>
    </testcase>
</testsuite>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(junit_xml)
        junit_path = Path(f.name)

    try:
        collector = TestResultCollector(junit_path)
        result = await collector.collect()

        # 10 tests, 2 failures, 1 error = 7 passed
        # Pass rate = 70%
        assert result.normalized_score == 70.0
        assert result.details["total"] == 10
        assert result.details["passed"] == 7
        assert result.details["failed"] == 2
        assert result.details["errors"] == 1
    finally:
        junit_path.unlink()


@pytest.mark.asyncio
async def test_test_collector_missing_file():
    """Test collector should handle missing file gracefully."""
    junit_path = Path("/nonexistent/junit.xml")
    collector = TestResultCollector(junit_path)
    result = await collector.collect()

    assert result.normalized_score == 0.0
    assert result.error_message is not None
    assert "not found" in result.error_message.lower()


@pytest.mark.asyncio
async def test_coverage_collector_positive_delta():
    """Coverage collector should reward coverage increases."""
    coverage_xml = """<?xml version="1.0"?>
<coverage line-rate="0.90" branch-rate="0.85" version="1.0">
    <packages></packages>
</coverage>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(coverage_xml)
        coverage_path = Path(f.name)

    try:
        # Current: 90%, Baseline: 85%, Delta: +5%
        collector = CoverageCollector(coverage_path, baseline_coverage=85.0)
        result = await collector.collect()

        assert result.category == MetricCategory.COVERAGE
        # +5% delta should give high score (near 100)
        assert result.normalized_score > 90.0
        assert result.details["current_coverage"] == "90.00%"
        assert result.details["baseline_coverage"] == "85.00%"
        assert "+5.00%" in result.details["delta"]
    finally:
        coverage_path.unlink()


@pytest.mark.asyncio
async def test_coverage_collector_negative_delta():
    """Coverage collector should penalize coverage decreases."""
    coverage_xml = """<?xml version="1.0"?>
<coverage line-rate="0.75" branch-rate="0.70" version="1.0">
    <packages></packages>
</coverage>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(coverage_xml)
        coverage_path = Path(f.name)

    try:
        # Current: 75%, Baseline: 85%, Delta: -10%
        collector = CoverageCollector(coverage_path, baseline_coverage=85.0)
        result = await collector.collect()

        # -10% delta should give low score
        assert result.normalized_score < 50.0
        assert "-10.00%" in result.details["delta"]
    finally:
        coverage_path.unlink()


@pytest.mark.asyncio
async def test_coverage_collector_tolerance_threshold():
    """Coverage collector should ignore small deltas within tolerance."""
    coverage_xml = """<?xml version="1.0"?>
<coverage line-rate="0.850" branch-rate="0.80" version="1.0">
    <packages></packages>
</coverage>"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(coverage_xml)
        coverage_path = Path(f.name)

    try:
        # Current: 85.0%, Baseline: 85.05%, Delta: -0.05% (within tolerance)
        collector = CoverageCollector(coverage_path, baseline_coverage=85.05, tolerance=0.1)
        result = await collector.collect()

        # Small delta should be treated as 0
        assert result.details["delta"] == "+0.00%"
        # Neutral score (50)
        assert 45.0 <= result.normalized_score <= 55.0
    finally:
        coverage_path.unlink()


@pytest.mark.asyncio
async def test_static_analysis_collector_no_errors():
    """Static analysis with no errors should return 100."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # Create empty ruff results (no errors)
        ruff_path = repo_root / "ruff.json"
        ruff_path.write_text("[]")

        # Create empty pyright results
        pyright_path = repo_root / "pyright.json"
        pyright_path.write_text('{"summary": {"errorCount": 0}}')

        collector = StaticAnalysisCollector(
            repo_root, ruff_results_path=ruff_path, pyright_results_path=pyright_path
        )
        result = await collector.collect()

        assert result.category == MetricCategory.STATIC_ANALYSIS
        assert result.normalized_score == 100.0
        assert result.details["total_errors"] == 0


@pytest.mark.asyncio
async def test_static_analysis_collector_few_errors():
    """Static analysis with 1-5 errors should return 80."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # 3 ruff errors
        ruff_path = repo_root / "ruff.json"
        ruff_path.write_text('[{"code": "E501"}, {"code": "F401"}, {"code": "W503"}]')

        # 2 pyright errors
        pyright_path = repo_root / "pyright.json"
        pyright_path.write_text('{"summary": {"errorCount": 2}}')

        collector = StaticAnalysisCollector(
            repo_root, ruff_results_path=ruff_path, pyright_results_path=pyright_path
        )
        result = await collector.collect()

        # Total: 5 errors → 80 score
        assert result.details["total_errors"] == 5
        assert result.normalized_score == 80.0


@pytest.mark.asyncio
async def test_static_analysis_collector_many_errors():
    """Static analysis with many errors should decay exponentially."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)

        # 20 errors total
        ruff_path = repo_root / "ruff.json"
        ruff_errors = [{"code": f"E{i}"} for i in range(10)]
        import json

        ruff_path.write_text(json.dumps(ruff_errors))

        pyright_path = repo_root / "pyright.json"
        pyright_path.write_text('{"summary": {"errorCount": 10}}')

        collector = StaticAnalysisCollector(
            repo_root, ruff_results_path=ruff_path, pyright_results_path=pyright_path
        )
        result = await collector.collect()

        assert result.details["total_errors"] == 20
        # With 20 errors, score should be significantly reduced
        assert result.normalized_score < 50.0


@pytest.mark.asyncio
async def test_ai_review_collector_no_issues():
    """AI review with no issues should return 100."""
    # Create result with no consensus issues
    review_result = MultiModelResult(
        test_id="test-1",
        model_results=[],
        consensus_issues=[],
        unanimous_issues=[],
        any_model_issues=[],
        consensus_passed=True,
        models_passed=3,
        total_models=3,
    )

    collector = AIReviewCollector(review_results=[review_result])
    result = await collector.collect()

    assert result.category == MetricCategory.AI_REVIEW
    assert result.normalized_score == 100.0
    assert result.details["total_consensus_issues"] == 0


@pytest.mark.asyncio
async def test_ai_review_collector_security_issues():
    """AI review with security issues should apply heavy penalty."""
    # Create result with security issues
    review_result = MultiModelResult(
        test_id="test-1",
        model_results=[],
        consensus_issues=["SQL injection vulnerability detected", "Potential XSS issue"],
        unanimous_issues=[],
        any_model_issues=["SQL injection vulnerability detected", "Potential XSS issue"],
        consensus_passed=False,
        models_passed=0,
        total_models=3,
    )

    collector = AIReviewCollector(review_results=[review_result])
    result = await collector.collect()

    # 2 security issues × 50 points = -100
    assert result.normalized_score == 0.0
    assert result.details["security_issues"] == 2
    assert result.details["total_consensus_issues"] == 2


@pytest.mark.asyncio
async def test_ai_review_collector_mixed_severity():
    """AI review should categorize issues by severity correctly."""
    review_result = MultiModelResult(
        test_id="test-1",
        model_results=[],
        consensus_issues=[
            "SQL injection found",  # Security: -50
            "Critical performance issue",  # High: -20
            "Consider refactoring this function",  # Medium: -5
            "Minor code style issue",  # Low: -1
        ],
        unanimous_issues=[],
        any_model_issues=[],
        consensus_passed=False,
        models_passed=0,
        total_models=3,
    )

    collector = AIReviewCollector(review_results=[review_result])
    result = await collector.collect()

    # Score: 100 - 50 - 20 - 5 - 1 = 24
    assert result.normalized_score == 24.0
    assert result.details["security_issues"] == 1
    assert result.details["high_severity"] == 1
    assert result.details["medium_severity"] == 1
    assert result.details["low_severity"] == 1
