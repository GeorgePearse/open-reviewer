"""Tests for SQL anti-pattern detection."""

import pytest
from conftest import load_fixture

from review_eval.evaluator import ReviewEvaluator
from review_eval.models import GoldenTestCase


@pytest.mark.parametrize(
    "fixture_file,expected_issues",
    [
        ("missing_is_prefix.sql", ["is_"]),
        ("varchar_n.sql", ["varchar"]),
        ("select_star.sql", ["SELECT *"]),
    ],
)
def test_sql_antipatterns(
    sql_evaluator: ReviewEvaluator,
    fixture_file: str,
    expected_issues: list[str],
) -> None:
    """Test that Claude catches SQL anti-patterns."""
    code = load_fixture("sql", fixture_file)
    test_case = GoldenTestCase(
        id=f"sql-{fixture_file}",
        file_path=f"fixtures/sql/{fixture_file}",
        code=code,
        expected_issues=expected_issues,
        category="sql",
    )

    result = sql_evaluator.evaluate(test_case)

    assert result.passed, (
        f"Failed to catch issues in {fixture_file}. Matched: {result.matched_issues}, Missed: {result.missed_issues}"
    )


def test_catches_boolean_naming(sql_evaluator: ReviewEvaluator) -> None:
    """Test that boolean columns without is_ prefix are flagged."""
    code = load_fixture("sql", "missing_is_prefix.sql")
    test_case = GoldenTestCase(
        id="sql-boolean-naming",
        file_path="fixtures/sql/missing_is_prefix.sql",
        code=code,
        expected_issues=["active", "verified", "deleted"],
        category="sql",
    )

    result = sql_evaluator.evaluate(test_case)

    # At least one of the bad column names should be mentioned
    review_lower = result.review_text.lower()
    found_any = any(issue.lower() in review_lower for issue in test_case.expected_issues)
    assert found_any, f"Failed to flag boolean columns. Response: {result.review_text[:500]}"


def test_catches_timestamp_without_timezone(sql_evaluator: ReviewEvaluator) -> None:
    """Test that TIMESTAMP without TIME ZONE is flagged."""
    code = load_fixture("sql", "select_star.sql")
    test_case = GoldenTestCase(
        id="sql-timestamp",
        file_path="fixtures/sql/select_star.sql",
        code=code,
        expected_issues=["time zone", "timezone"],
        category="sql",
    )

    result = sql_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    found_timezone = "time zone" in review_lower or "timezone" in review_lower
    assert found_timezone, (
        f"Failed to flag TIMESTAMP without TIME ZONE. Response: {result.review_text[:500]}"
    )
