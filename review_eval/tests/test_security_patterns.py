"""Tests for security vulnerability detection."""

import pytest
from conftest import load_fixture

from review_eval.evaluator import ReviewEvaluator
from review_eval.models import GoldenTestCase


@pytest.mark.parametrize(
    "fixture_file,expected_issues",
    [
        ("sql_injection.py", ["injection"]),
        ("hardcoded_secret.py", ["secret"]),
        ("command_injection.py", ["injection"]),
    ],
)
def test_security_vulnerabilities(
    security_evaluator: ReviewEvaluator,
    fixture_file: str,
    expected_issues: list[str],
) -> None:
    """Test that Claude catches security vulnerabilities."""
    code = load_fixture("security", fixture_file)
    test_case = GoldenTestCase(
        id=f"security-{fixture_file}",
        file_path=f"fixtures/security/{fixture_file}",
        code=code,
        expected_issues=expected_issues,
        category="security",
    )

    result = security_evaluator.evaluate(test_case)

    assert result.passed, (
        f"Failed to catch issues in {fixture_file}. Matched: {result.matched_issues}, Missed: {result.missed_issues}"
    )


def test_catches_sql_injection_details(security_evaluator: ReviewEvaluator) -> None:
    """Test that SQL injection review mentions specific patterns."""
    code = load_fixture("security", "sql_injection.py")
    test_case = GoldenTestCase(
        id="security-sql-injection-details",
        file_path="fixtures/security/sql_injection.py",
        code=code,
        expected_issues=["f-string", "format", "parameterized"],
        category="security",
    )

    result = security_evaluator.evaluate(test_case)

    # Should mention at least one of the problematic patterns or the fix
    review_lower = result.review_text.lower()
    found_any = any(issue.lower() in review_lower for issue in test_case.expected_issues)
    assert found_any, f"Failed to explain SQL injection. Response: {result.review_text[:500]}"


def test_catches_hardcoded_api_keys(security_evaluator: ReviewEvaluator) -> None:
    """Test that hardcoded API keys are flagged."""
    code = load_fixture("security", "hardcoded_secret.py")
    test_case = GoldenTestCase(
        id="security-hardcoded-keys",
        file_path="fixtures/security/hardcoded_secret.py",
        code=code,
        expected_issues=["API_KEY", "hardcoded", "environment"],
        category="security",
    )

    result = security_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    found_hardcoded = (
        "hardcoded" in review_lower or "hard-coded" in review_lower or "hard coded" in review_lower
    )
    assert found_hardcoded, (
        f"Failed to flag hardcoded secrets. Response: {result.review_text[:500]}"
    )


def test_catches_shell_injection(security_evaluator: ReviewEvaluator) -> None:
    """Test that shell=True with user input is flagged."""
    code = load_fixture("security", "command_injection.py")
    test_case = GoldenTestCase(
        id="security-shell-injection",
        file_path="fixtures/security/command_injection.py",
        code=code,
        expected_issues=["shell=True", "shell"],
        category="security",
    )

    result = security_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    found_shell = "shell" in review_lower
    assert found_shell, f"Failed to flag shell=True. Response: {result.review_text[:500]}"
