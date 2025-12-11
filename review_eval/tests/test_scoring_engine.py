"""Tests for the PR scoring engine."""

import pytest

from review_eval.collectors.base import MetricCollector
from review_eval.models import MetricCategory, ScoringConfig, ScoringResult
from review_eval.scoring_engine import ScoringEngine


class MockCollector(MetricCollector):
    """Mock collector for testing."""

    def __init__(
        self,
        category: MetricCategory,
        score: float,
        raw_value: float = 0.0,
        details: dict | None = None,
        weight: float = 0.25,
    ):
        super().__init__(category, weight)
        self._score = score
        self._raw_value = raw_value
        self._details = details or {}

    async def collect(self) -> ScoringResult:
        return self._create_result(
            raw_value=self._raw_value,
            normalized_score=self._score,
            details=self._details,
        )


@pytest.mark.asyncio
async def test_scoring_with_perfect_metrics():
    """All metrics at 100 should yield 100 score."""
    config = ScoringConfig(
        threshold=80.0,
        weights={
            MetricCategory.TESTS: 0.25,
            MetricCategory.COVERAGE: 0.25,
            MetricCategory.STATIC_ANALYSIS: 0.25,
            MetricCategory.AI_REVIEW: 0.25,
        },
    )

    collectors = [
        MockCollector(MetricCategory.TESTS, 100.0, weight=0.25),
        MockCollector(MetricCategory.COVERAGE, 100.0, weight=0.25),
        MockCollector(MetricCategory.STATIC_ANALYSIS, 100.0, weight=0.25),
        MockCollector(MetricCategory.AI_REVIEW, 100.0, weight=0.25),
    ]

    engine = ScoringEngine(config, collectors)
    result = await engine.calculate_score()

    assert result.total_score == 100.0
    assert result.status == "PASS"
    assert len(result.blocking_factors) == 0


@pytest.mark.asyncio
async def test_scoring_with_weighted_metrics():
    """Test weighted average calculation."""
    config = ScoringConfig(
        threshold=80.0,
        weights={
            MetricCategory.TESTS: 0.30,
            MetricCategory.COVERAGE: 0.20,
            MetricCategory.STATIC_ANALYSIS: 0.20,
            MetricCategory.AI_REVIEW: 0.30,
        },
    )

    collectors = [
        MockCollector(MetricCategory.TESTS, 90.0, weight=0.30),  # 90 * 0.30 = 27
        MockCollector(MetricCategory.COVERAGE, 80.0, weight=0.20),  # 80 * 0.20 = 16
        MockCollector(MetricCategory.STATIC_ANALYSIS, 70.0, weight=0.20),  # 70 * 0.20 = 14
        MockCollector(MetricCategory.AI_REVIEW, 100.0, weight=0.30),  # 100 * 0.30 = 30
    ]
    # Expected: 27 + 16 + 14 + 30 = 87

    engine = ScoringEngine(config, collectors)
    result = await engine.calculate_score()

    assert result.total_score == pytest.approx(87.0, abs=0.1)
    assert result.status == "PASS"


@pytest.mark.asyncio
async def test_security_penalty_causes_failure():
    """Security vulnerability should result in FAIL status."""
    config = ScoringConfig(
        threshold=80.0,
        weights={
            MetricCategory.TESTS: 0.30,
            MetricCategory.COVERAGE: 0.20,
            MetricCategory.STATIC_ANALYSIS: 0.20,
            MetricCategory.AI_REVIEW: 0.30,
        },
        critical_penalties={
            "security_vulnerability": 100.0,
        },
    )

    collectors = [
        MockCollector(MetricCategory.TESTS, 100.0, weight=0.30),
        MockCollector(MetricCategory.COVERAGE, 100.0, weight=0.20),
        MockCollector(MetricCategory.STATIC_ANALYSIS, 100.0, weight=0.20),
        MockCollector(
            MetricCategory.AI_REVIEW,
            100.0,
            details={"security_issues": 1},
            weight=0.30,
        ),
    ]

    engine = ScoringEngine(config, collectors)
    result = await engine.calculate_score()

    # Score should be 0 after -100 penalty
    assert result.total_score == 0.0
    assert result.status == "FAIL"
    assert len(result.blocking_factors) > 0
    assert "Security vulnerability" in result.blocking_factors[0]


@pytest.mark.asyncio
async def test_critical_test_failure_penalty():
    """All tests failing should apply penalty."""
    config = ScoringConfig(
        threshold=80.0,
        weights={
            MetricCategory.TESTS: 0.30,
            MetricCategory.COVERAGE: 0.20,
            MetricCategory.STATIC_ANALYSIS: 0.20,
            MetricCategory.AI_REVIEW: 0.30,
        },
        critical_penalties={
            "critical_test_failure": 50.0,
        },
    )

    collectors = [
        MockCollector(
            MetricCategory.TESTS,
            0.0,
            details={"total": 10, "failed": 10, "passed": 0},
            weight=0.30,
        ),
        MockCollector(MetricCategory.COVERAGE, 100.0, weight=0.20),
        MockCollector(MetricCategory.STATIC_ANALYSIS, 100.0, weight=0.20),
        MockCollector(MetricCategory.AI_REVIEW, 100.0, weight=0.30),
    ]
    # Base score: 0*0.30 + 100*0.20 + 100*0.20 + 100*0.30 = 70
    # Penalty: -50
    # Final: 20

    engine = ScoringEngine(config, collectors)
    result = await engine.calculate_score()

    assert result.total_score == 20.0
    assert result.status == "FAIL"
    assert "All tests failing" in result.blocking_factors[0]


@pytest.mark.asyncio
async def test_score_below_threshold_fails():
    """Score below threshold should fail even without blocking factors."""
    config = ScoringConfig(threshold=80.0)

    collectors = [
        MockCollector(MetricCategory.TESTS, 60.0, weight=0.30),
        MockCollector(MetricCategory.COVERAGE, 70.0, weight=0.20),
        MockCollector(MetricCategory.STATIC_ANALYSIS, 65.0, weight=0.20),
        MockCollector(MetricCategory.AI_REVIEW, 75.0, weight=0.30),
    ]
    # Score: 60*0.30 + 70*0.20 + 65*0.20 + 75*0.30 = 18 + 14 + 13 + 22.5 = 67.5

    engine = ScoringEngine(config, collectors)
    result = await engine.calculate_score()

    assert result.total_score == pytest.approx(67.5, abs=0.1)
    assert result.status == "FAIL"


@pytest.mark.asyncio
async def test_config_validation_fails_for_invalid_weights():
    """Config with invalid weights should raise error."""
    config = ScoringConfig(
        weights={
            MetricCategory.TESTS: 0.50,
            MetricCategory.COVERAGE: 0.30,
            MetricCategory.STATIC_ANALYSIS: 0.30,  # Sum = 1.10 (invalid)
            MetricCategory.AI_REVIEW: 0.00,
        }
    )

    collectors = [MockCollector(MetricCategory.TESTS, 100.0)]

    with pytest.raises(ValueError, match="Weights must sum to 1.0"):
        ScoringEngine(config, collectors)


@pytest.mark.asyncio
async def test_score_clamped_to_range():
    """Score should be clamped to [0, 100] range."""
    config = ScoringConfig(
        threshold=80.0,
        weights={
            MetricCategory.TESTS: 1.0,
        },
    )

    # Test upper bound
    collectors = [MockCollector(MetricCategory.TESTS, 150.0, weight=1.0)]  # Unrealistic
    engine = ScoringEngine(config, collectors)
    result = await engine.calculate_score()
    assert result.total_score <= 100.0

    # Test lower bound with large penalty
    config_penalty = ScoringConfig(
        threshold=80.0,
        weights={MetricCategory.TESTS: 1.0},
        critical_penalties={"security_vulnerability": 200.0},
    )
    collectors_penalty = [
        MockCollector(MetricCategory.TESTS, 50.0, details={"security_issues": 2}, weight=1.0)
    ]
    engine_penalty = ScoringEngine(config_penalty, collectors_penalty)
    result_penalty = await engine_penalty.calculate_score()
    assert result_penalty.total_score >= 0.0


@pytest.mark.asyncio
async def test_breakdown_contains_all_categories():
    """Result breakdown should include all collected metrics."""
    config = ScoringConfig()

    collectors = [
        MockCollector(MetricCategory.TESTS, 85.0, weight=0.30),
        MockCollector(MetricCategory.COVERAGE, 90.0, weight=0.20),
    ]

    engine = ScoringEngine(config, collectors)
    result = await engine.calculate_score()

    assert MetricCategory.TESTS in result.breakdown
    assert MetricCategory.COVERAGE in result.breakdown
    assert result.breakdown[MetricCategory.TESTS].normalized_score == 85.0
    assert result.breakdown[MetricCategory.COVERAGE].normalized_score == 90.0
