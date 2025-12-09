"""Tests for Python async/await anti-pattern detection."""

import pytest
from conftest import load_fixture

from review_eval.evaluator import ReviewEvaluator
from review_eval.models import GoldenTestCase


@pytest.fixture
def async_evaluator() -> ReviewEvaluator:
    """Create evaluator with async/await-specific review context."""
    prompt = """You are reviewing Python async/await code for the BinIt monorepo.
Flag these async/await anti-patterns:
- Missing await on coroutine calls (returns coroutine object)
- Using time.sleep() in async functions (use asyncio.sleep instead)
- Using requests library in async functions (use aiohttp instead)
- Calling asyncio.run() inside async context (not allowed)
- Fire-and-forget asyncio.create_task() without proper reference or error handling
- Sync iteration over async iterators (need async for loop)
- Mixing blocking and async operations

Be explicit about what issues you find. Mention the specific anti-pattern names."""
    return ReviewEvaluator(prompt)


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
    """Test that missing await on coroutines is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="async-missing-await",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["await", "coroutine"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    # Should mention await or coroutine issues
    review_lower = result.review_text.lower()
    assert "await" in review_lower or "coroutine" in review_lower, (
        f"Should catch missing await. Response: {result.review_text[:500]}"
    )


def test_catches_blocking_calls(async_evaluator: ReviewEvaluator) -> None:
    """Test that blocking calls in async functions are detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="async-blocking-calls",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["time.sleep", "requests", "blocking"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    # Should mention blocking operations
    review_lower = result.review_text.lower()
    blocking_mentioned = any(
        term in review_lower
        for term in ["time.sleep", "requests", "blocking", "asyncio.sleep", "aiohttp"]
    )
    assert blocking_mentioned, (
        f"Should catch blocking calls. Response: {result.review_text[:500]}"
    )


def test_catches_event_loop_issues(async_evaluator: ReviewEvaluator) -> None:
    """Test that event loop misuse is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="async-event-loop",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["asyncio.run", "event loop", "nested"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    # Should mention event loop issues
    review_lower = result.review_text.lower()
    loop_mentioned = any(
        term in review_lower
        for term in ["asyncio.run", "event loop", "nested", "async context"]
    )
    assert loop_mentioned, (
        f"Should catch event loop issues. Response: {result.review_text[:500]}"
    )


def test_catches_fire_and_forget(async_evaluator: ReviewEvaluator) -> None:
    """Test that fire-and-forget tasks are detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="async-fire-forget",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["create_task", "fire", "reference", "error handling"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    # Should mention task management issues
    review_lower = result.review_text.lower()
    task_mentioned = any(
        term in review_lower
        for term in ["create_task", "fire", "forget", "reference", "error"]
    )
    assert task_mentioned, (
        f"Should catch fire-and-forget issues. Response: {result.review_text[:500]}"
    )


def test_catches_sync_async_iteration(async_evaluator: ReviewEvaluator) -> None:
    """Test that sync iteration over async iterators is detected."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="async-iteration",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=["async for", "async iterator", "sync iteration"],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    # Should mention iteration issues
    review_lower = result.review_text.lower()
    iteration_mentioned = any(
        term in review_lower
        for term in ["async for", "iterator", "iteration", "async generator"]
    )
    assert iteration_mentioned, (
        f"Should catch iteration issues. Response: {result.review_text[:500]}"
    )


def test_comprehensive_async_issues(async_evaluator: ReviewEvaluator) -> None:
    """Test that multiple async issues are caught comprehensively."""
    code = load_fixture("python", "async_await_issues.py")
    test_case = GoldenTestCase(
        id="async-comprehensive",
        file_path="fixtures/python/async_await_issues.py",
        code=code,
        expected_issues=[
            "await", "asyncio.sleep", "aiohttp", "asyncio.run",
            "create_task", "async for"
        ],
        category="python-async",
    )

    result = async_evaluator.evaluate(test_case)

    # Should catch at least half of the expected issues
    matched_count = len(result.matched_issues)
    expected_count = len(test_case.expected_issues)

    assert matched_count >= expected_count // 2, (
        f"Should catch multiple async issues. "
        f"Matched {matched_count}/{expected_count}: {result.matched_issues}"
    )