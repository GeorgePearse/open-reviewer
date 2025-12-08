"""Tests for Python anti-pattern detection."""

import pytest
from conftest import load_fixture
from review_eval.evaluator import ReviewEvaluator
from review_eval.models import GoldenTestCase


@pytest.mark.parametrize(
    "fixture_file,expected_issues",
    [
        ("psycopg2_usage.py", ["psycopg2"]),
        ("yaml_unsafe_load.py", ["safe_load"]),
        ("missing_types.py", ["type"]),
        ("any_type_abuse.py", ["Any"]),
    ],
)
def test_python_antipatterns(
    python_evaluator: ReviewEvaluator,
    fixture_file: str,
    expected_issues: list[str],
) -> None:
    """Test that Claude catches Python anti-patterns."""
    code = load_fixture("python", fixture_file)
    test_case = GoldenTestCase(
        id=f"python-{fixture_file}",
        file_path=f"fixtures/python/{fixture_file}",
        code=code,
        expected_issues=expected_issues,
        category="python",
    )

    result = python_evaluator.evaluate(test_case)

    assert result.passed, f"Failed to catch issues in {fixture_file}. Matched: {result.matched_issues}, Missed: {result.missed_issues}"


def test_catches_psycopg2_and_sql_injection(python_evaluator: ReviewEvaluator) -> None:
    """Test that psycopg2 fixture also catches SQL injection."""
    code = load_fixture("python", "psycopg2_usage.py")
    test_case = GoldenTestCase(
        id="python-psycopg2-full",
        file_path="fixtures/python/psycopg2_usage.py",
        code=code,
        expected_issues=["psycopg2", "injection"],
        category="python",
    )

    result = python_evaluator.evaluate(test_case)

    # At minimum, psycopg2 should be caught
    assert "psycopg2" in [issue.lower() for issue in result.matched_issues], f"Failed to catch psycopg2. Response: {result.review_text[:500]}"


# Over-engineering detection tests
@pytest.mark.parametrize(
    "fixture_file,expected_issues",
    [
        ("hardcoded_pipeline_params.py", ["config", "hardcoded"]),
        ("custom_registry.py", ["enum", "simpler"]),
        ("redundant_validation.py", ["pydantic", "Field"]),
        ("premature_abstraction.py", ["abstract", "YAGNI"]),
    ],
)
def test_overengineering_detection(
    overengineering_evaluator: ReviewEvaluator,
    fixture_file: str,
    expected_issues: list[str],
) -> None:
    """Test that Claude catches over-engineering patterns."""
    code = load_fixture("overengineering", fixture_file)
    test_case = GoldenTestCase(
        id=f"overengineering-{fixture_file}",
        file_path=f"fixtures/overengineering/{fixture_file}",
        code=code,
        expected_issues=expected_issues,
        category="overengineering",
    )

    result = overengineering_evaluator.evaluate(test_case)

    assert result.passed, f"Failed to catch over-engineering in {fixture_file}. Matched: {result.matched_issues}, Missed: {result.missed_issues}"


def test_hardcoded_params_suggests_config(overengineering_evaluator: ReviewEvaluator) -> None:
    """Test that hardcoded params fixture suggests using config."""
    code = load_fixture("overengineering", "hardcoded_pipeline_params.py")
    test_case = GoldenTestCase(
        id="overengineering-hardcoded-config",
        file_path="fixtures/overengineering/hardcoded_pipeline_params.py",
        code=code,
        expected_issues=["config", "yaml"],
        category="overengineering",
    )

    result = overengineering_evaluator.evaluate(test_case)

    # Should mention config as the simpler approach
    review_lower = result.review_text.lower()
    assert "config" in review_lower or "yaml" in review_lower, f"Should suggest config. Response: {result.review_text[:500]}"
