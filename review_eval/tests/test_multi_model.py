"""Tests for multi-model evaluation using OpenRouter."""

import pytest
from conftest import load_fixture

from review_eval.models import GoldenTestCase, ModelConfig
from review_eval.multi_model_evaluator import MultiModelEvaluator, print_multi_model_report

# Use a smaller set of models for faster testing
TEST_MODELS = [
    ModelConfig(name="Claude 3.5 Sonnet", model_id="anthropic/claude-3.5-sonnet"),
    ModelConfig(name="GPT-4o", model_id="openai/gpt-4o"),
    ModelConfig(name="Gemini 2.0 Flash", model_id="google/gemini-2.0-flash-001"),
]


@pytest.fixture
def multi_model_security_evaluator() -> MultiModelEvaluator:
    """Create multi-model evaluator with security-focused prompt."""
    prompt = """You are a security-focused code reviewer for the BinIt monorepo.
Flag these security issues:
- SQL injection via string formatting (f-strings, .format())
- Hardcoded secrets or API keys
- Command injection via subprocess with shell=True
- yaml.load() (allows arbitrary code execution)

Be explicit about what issues you find. Mention the specific vulnerability names."""
    return MultiModelEvaluator(prompt, models=TEST_MODELS)


@pytest.fixture
def multi_model_python_evaluator() -> MultiModelEvaluator:
    """Create multi-model evaluator with Python-specific context."""
    prompt = """You are reviewing Python code for the BinIt monorepo.
Flag these anti-patterns:
- psycopg2 (use psycopg3/psycopg instead)
- yaml.load() (use yaml.safe_load())
- Missing type annotations on functions
- Any types without justification

Be explicit about what issues you find."""
    return MultiModelEvaluator(prompt, models=TEST_MODELS)


@pytest.mark.asyncio
async def test_multi_model_sql_injection(
    multi_model_security_evaluator: MultiModelEvaluator,
) -> None:
    """Test that multiple models catch SQL injection."""
    code = load_fixture("security", "sql_injection.py")
    test_case = GoldenTestCase(
        id="multi-sql-injection",
        file_path="fixtures/security/sql_injection.py",
        code=code,
        expected_issues=["injection"],
        category="security",
    )

    result = await multi_model_security_evaluator.evaluate_async(test_case)

    print_multi_model_report(result)

    # At least majority should catch SQL injection
    assert result.models_passed >= len(TEST_MODELS) // 2, (
        f"Less than half caught SQL injection. Pass rate: {result.pass_rate:.0%}"
    )
    assert "injection" in [issue.lower() for issue in result.consensus_issues], (
        "SQL injection not in consensus"
    )


@pytest.mark.asyncio
async def test_multi_model_hardcoded_secrets(
    multi_model_security_evaluator: MultiModelEvaluator,
) -> None:
    """Test that multiple models catch hardcoded secrets."""
    code = load_fixture("security", "hardcoded_secret.py")
    test_case = GoldenTestCase(
        id="multi-hardcoded-secrets",
        file_path="fixtures/security/hardcoded_secret.py",
        code=code,
        expected_issues=["secret", "hardcoded"],
        category="security",
    )

    result = await multi_model_security_evaluator.evaluate_async(test_case)

    print_multi_model_report(result)

    # All models should catch hardcoded secrets
    assert result.pass_rate >= 0.5, (
        f"Less than half caught hardcoded secrets. Pass rate: {result.pass_rate:.0%}"
    )


@pytest.mark.asyncio
async def test_multi_model_psycopg2(multi_model_python_evaluator: MultiModelEvaluator) -> None:
    """Test that multiple models catch psycopg2 usage."""
    code = load_fixture("python", "psycopg2_usage.py")
    test_case = GoldenTestCase(
        id="multi-psycopg2",
        file_path="fixtures/python/psycopg2_usage.py",
        code=code,
        expected_issues=["psycopg2"],
        category="python",
    )

    result = await multi_model_python_evaluator.evaluate_async(test_case)

    print_multi_model_report(result)

    # Majority should catch psycopg2
    assert result.models_passed >= len(TEST_MODELS) // 2, (
        f"Less than half caught psycopg2. Pass rate: {result.pass_rate:.0%}"
    )


@pytest.mark.asyncio
async def test_model_agreement_comparison() -> None:
    """Compare model agreement across different issue types."""
    prompt = """You are a code reviewer. Flag any issues you see with:
- Security vulnerabilities
- Anti-patterns
- Missing best practices

Be explicit and specific about issues."""

    evaluator = MultiModelEvaluator(prompt, models=TEST_MODELS)

    # Test with SQL injection (should have high agreement)
    sql_code = load_fixture("security", "sql_injection.py")
    sql_case = GoldenTestCase(
        id="agreement-sql",
        file_path="fixtures/security/sql_injection.py",
        code=sql_code,
        expected_issues=["injection", "SQL"],
        category="security",
    )

    result = await evaluator.evaluate_async(sql_case)

    print("\n" + "=" * 60)
    print("Model Agreement Analysis")
    print("=" * 60)
    print(f"Unanimous issues: {result.unanimous_issues}")
    print(f"Consensus issues: {result.consensus_issues}")
    print(f"Any model found:  {result.any_model_issues}")
    print(
        f"Agreement rate:   {len(result.unanimous_issues)}/{len(result.any_model_issues)} issues unanimous"
    )
