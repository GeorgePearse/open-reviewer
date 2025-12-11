"""Tests for Python async/await anti-pattern detection."""

import pytest
from conftest import load_fixture

from review_eval.evaluator import ReviewEvaluator
from review_eval.models import GoldenTestCase


@pytest.mark.parametrize(
    "fixture_file,expected_issues",
    [
        ("async_await_issues.py", ["await", "asyncio.sleep", "aiohttp"]),
    ],
)
def test_async_antipatterns(
    async_evaluator: ReviewEvaluator,
    fixture_file: str,
    expected_issues: list[str],
) -> None:
    """Test that Claude catches async/await anti-patterns."""
    code = load_fixture("python", fixture_file)
    test_case = GoldenTestCase(
        id=f"python-async-{fixture_file}",
        file_path=f"fixtures/python/{fixture_file}",
        code=code,
        expected_issues=expected_issues,
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    assert result.passed, (
        f"Failed to catch async issues in {fixture_file}. "
        f"Matched: {result.matched_issues}, Missed: {result.missed_issues}"
    )


def test_catches_missing_await(async_evaluator: ReviewEvaluator) -> None:
    """Test that missing await on coroutine calls is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="python-async-missing-await",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["await", "coroutine"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    assert "await" in review_lower, (
        f"Should catch missing await. Response: {result.review_text[:500]}"
    )


def test_catches_blocking_sleep(async_evaluator: ReviewEvaluator) -> None:
    """Test that blocking time.sleep in async function is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="python-async-blocking-sleep",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["time.sleep", "asyncio.sleep", "blocking"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    assert any(keyword in review_lower for keyword in ["time.sleep", "asyncio.sleep", "blocking"]), (
        f"Should catch blocking sleep. Response: {result.review_text[:500]}"
    )


def test_catches_blocking_requests(async_evaluator: ReviewEvaluator) -> None:
    """Test that blocking requests in async function is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="python-async-blocking-requests",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["requests", "aiohttp", "blocking"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    assert any(keyword in review_lower for keyword in ["requests", "aiohttp", "blocking"]), (
        f"Should catch blocking requests. Response: {result.review_text[:500]}"
    )


def test_catches_nested_asyncio_run(async_evaluator: ReviewEvaluator) -> None:
    """Test that asyncio.run() in async context is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="python-async-nested-run",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["asyncio.run", "event loop", "RuntimeError"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    assert any(keyword in review_lower for keyword in ["asyncio.run", "event loop", "runtime"]), (
        f"Should catch nested asyncio.run. Response: {result.review_text[:500]}"
    )


def test_catches_fire_and_forget_tasks(async_evaluator: ReviewEvaluator) -> None:
    """Test that fire-and-forget create_task is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="python-async-fire-forget",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["create_task", "reference", "garbage"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    assert any(keyword in review_lower for keyword in ["create_task", "reference", "garbage"]), (
        f"Should catch fire-and-forget tasks. Response: {result.review_text[:500]}"
    )


def test_catches_sync_iteration_over_async(async_evaluator: ReviewEvaluator) -> None:
    """Test that sync iteration over async iterator is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="python-async-sync-iteration",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["async for", "async generator", "iteration"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    review_lower = result.review_text.lower()
    assert any(keyword in review_lower for keyword in ["async for", "generator", "iteration"]), (
        f"Should catch sync iteration over async. Response: {result.review_text[:500]}"
    )