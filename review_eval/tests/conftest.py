"""Pytest configuration and shared fixtures for review evaluation tests."""

from pathlib import Path

import pytest
from review_eval.evaluator import ReviewEvaluator

FIXTURES_DIR = Path(__file__).parent.parent / "review_eval" / "fixtures"


@pytest.fixture
def python_evaluator() -> ReviewEvaluator:
    """Create evaluator with Python-specific review context."""
    prompt = """You are reviewing Python code for the BinIt monorepo.
Flag these anti-patterns:
- psycopg2 (use psycopg3/psycopg instead)
- yaml.load() (use yaml.safe_load())
- Missing type annotations on functions
- Any types without justification
- utils/misc modules (create purposeful packages instead)

Be explicit about what issues you find. Mention the specific anti-pattern names."""
    return ReviewEvaluator(prompt)


@pytest.fixture
def typescript_evaluator() -> ReviewEvaluator:
    """Create evaluator with TypeScript-specific review context."""
    prompt = """You are reviewing TypeScript code for the BinIt monorepo.
Flag these anti-patterns:
- Raw fetch() instead of apiFetch/getJson helpers
- any types (use specific types instead)
- Default exports (prefer named exports)
- Direct Postgres queries (use GraphQL instead)

Be explicit about what issues you find. Mention the specific anti-pattern names."""
    return ReviewEvaluator(prompt)


@pytest.fixture
def sql_evaluator() -> ReviewEvaluator:
    """Create evaluator with SQL-specific review context."""
    prompt = """You are reviewing SQL code for the BinIt monorepo.
Flag these anti-patterns:
- Boolean columns without is_ prefix
- varchar(n) instead of TEXT
- SELECT * instead of explicit columns
- TIMESTAMP without TIME ZONE

Be explicit about what issues you find. Mention the specific anti-pattern names."""
    return ReviewEvaluator(prompt)


@pytest.fixture
def security_evaluator() -> ReviewEvaluator:
    """Create evaluator with security-focused review context."""
    prompt = """You are a security-focused code reviewer for the BinIt monorepo.
Flag these security issues:
- SQL injection via string formatting (f-strings, .format())
- Hardcoded secrets or API keys
- Command injection via subprocess with shell=True
- yaml.load() (allows arbitrary code execution)

Be explicit about what issues you find. Mention the specific vulnerability names."""
    return ReviewEvaluator(prompt)


@pytest.fixture
def overengineering_evaluator() -> ReviewEvaluator:
    """Create evaluator for detecting over-engineered code."""
    prompt = """You are reviewing Python code for unnecessary complexity and over-engineering.
Flag these anti-patterns:
- Singleton pattern when a module-level variable would suffice
- Factory pattern for 2-3 simple types (use dict/conditional instead)
- Abstract base classes with single implementation (premature abstraction)
- Hardcoded values that should be in config files (YAML/JSON config)
- Manual validation when Pydantic Field() constraints work
- Custom registries when a simple Enum would work
- Enterprise patterns (registry, factory, builder) for simple problems

When you identify over-engineering, explain what simpler approach would work.
Be explicit: use words like "simpler", "over-engineer", "unnecessary", "YAGNI", "premature"."""
    return ReviewEvaluator(prompt)


# Repo root for docs-aware tests (navigate up from tests dir)
# tests -> review_eval -> python -> lib -> repo_root
REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent


def load_fixture(category: str, filename: str) -> str:
    """Load a fixture file's contents."""
    fixture_path = FIXTURES_DIR / category / filename
    return fixture_path.read_text()
