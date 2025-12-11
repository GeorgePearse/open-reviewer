"""Tests for TypeScript anti-pattern detection."""

import pytest
from conftest import load_fixture

from review_eval.evaluator import ReviewEvaluator
from review_eval.models import GoldenTestCase


@pytest.mark.parametrize(
    "fixture_file,expected_issues",
    [
        ("raw_fetch.ts", ["fetch"]),
        ("any_types.ts", ["any"]),
        ("default_export.tsx", ["default"]),
        ("direct_postgres.ts", ["postgres"]),
    ],
)
def test_typescript_antipatterns(
    typescript_evaluator: ReviewEvaluator,
    fixture_file: str,
    expected_issues: list[str],
) -> None:
    """Test that Claude catches TypeScript anti-patterns."""
    code = load_fixture("typescript", fixture_file)
    test_case = GoldenTestCase(
        id=f"typescript-{fixture_file}",
        file_path=f"fixtures/typescript/{fixture_file}",
        code=code,
        expected_issues=expected_issues,
        category="typescript",
    )

    result = typescript_evaluator.evaluate(test_case)

    assert result.passed, (
        f"Failed to catch issues in {fixture_file}. Matched: {result.matched_issues}, Missed: {result.missed_issues}"
    )


def test_catches_graphql_suggestion(typescript_evaluator: ReviewEvaluator) -> None:
    """Test that direct Postgres usage suggests GraphQL alternative."""
    code = load_fixture("typescript", "direct_postgres.ts")
    test_case = GoldenTestCase(
        id="typescript-postgres-graphql",
        file_path="fixtures/typescript/direct_postgres.ts",
        code=code,
        expected_issues=["graphql"],
        category="typescript",
    )

    result = typescript_evaluator.evaluate(test_case)

    # GraphQL should be mentioned as the alternative
    assert "graphql" in result.review_text.lower(), (
        f"Failed to suggest GraphQL. Response: {result.review_text[:500]}"
    )
