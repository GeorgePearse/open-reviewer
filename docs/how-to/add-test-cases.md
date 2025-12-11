# Add Test Cases

Create custom golden test cases for your codebase.

## What is a Golden Test Case?

A golden test case contains:

- **Known-bad code** - Code with specific issues
- **Expected issues** - Keywords the review MUST mention
- **Category** - Type of anti-pattern

## Create a Basic Test Case

```python
from review_eval import GoldenTestCase

test_case = GoldenTestCase(
    id="my-custom-test",
    file_path="fixtures/my_test.py",
    code='''
def process(data):
    return data.upper()
''',
    expected_issues=["type annotation", "type hint"],
    category="python",
)
```

## Fields Explained

### id

Unique identifier for the test:

```python
id="python-missing-types-function"
```

### file_path

Reference path (can be to actual fixture file or just descriptive):

```python
file_path="fixtures/python/missing_types.py"
```

### code

The code snippet to review:

```python
code='''
import yaml

data = yaml.load(open("config.yml"))
'''
```

### expected_issues

Keywords that MUST appear in the review. Case-insensitive matching:

```python
expected_issues=["safe_load", "yaml.load"]
```

!!! tip
    Use general keywords that any reasonable review would include.
    Avoid very specific phrases that might not appear verbatim.

### severity

Optional severity level:

```python
severity="high"     # Critical issues
severity="medium"   # Important but not critical
severity="low"      # Minor issues
```

### category

Group your tests:

```python
category="python"      # Python anti-patterns
category="typescript"  # TypeScript issues
category="sql"         # SQL problems
category="security"    # Security vulnerabilities
category="custom"      # Your own category
```

## Add to Test Suite

### Method 1: Inline in Tests

```python
# tests/test_my_patterns.py
import pytest
from review_eval import ReviewEvaluator, GoldenTestCase

@pytest.fixture
def evaluator():
    return ReviewEvaluator(
        prompt_context="Review this code for issues."
    )

def test_missing_types(evaluator):
    test_case = GoldenTestCase(
        id="missing-types",
        file_path="example.py",
        code="def foo(x): return x * 2",
        expected_issues=["type"],
        category="python",
    )
    result = evaluator.evaluate(test_case)
    assert result.passed

def test_sql_injection(evaluator):
    test_case = GoldenTestCase(
        id="sql-injection",
        file_path="query.py",
        code='query = f"SELECT * FROM users WHERE id = {id}"',
        expected_issues=["injection", "parameterized"],
        category="security",
    )
    result = evaluator.evaluate(test_case)
    assert result.passed
```

### Method 2: Fixture Files

Create fixture files in `fixtures/`:

```python
# fixtures/python/my_pattern.py
def problematic_function():
    """This function has issues."""
    import subprocess
    subprocess.run(user_input, shell=True)  # Command injection!
```

Reference in tests:

```python
from pathlib import Path

def test_command_injection(evaluator):
    fixture = Path("fixtures/python/my_pattern.py")
    test_case = GoldenTestCase(
        id="command-injection",
        file_path=str(fixture),
        code=fixture.read_text(),
        expected_issues=["shell=True", "injection", "subprocess"],
        category="security",
    )
    result = evaluator.evaluate(test_case)
    assert result.passed
```

### Method 3: Parametrized Tests

Test multiple patterns with one function:

```python
import pytest

PATTERNS = [
    GoldenTestCase(
        id="yaml-unsafe",
        file_path="yaml.py",
        code="yaml.load(f)",
        expected_issues=["safe_load"],
        category="security",
    ),
    GoldenTestCase(
        id="psycopg2",
        file_path="db.py",
        code="import psycopg2",
        expected_issues=["psycopg3", "deprecated"],
        category="python",
    ),
]

@pytest.mark.parametrize("test_case", PATTERNS, ids=lambda t: t.id)
def test_patterns(evaluator, test_case):
    result = evaluator.evaluate(test_case)
    assert result.passed, f"Missed: {result.missed_issues}"
```

## Best Practices

### 1. Use Broad Keywords

```python
# Good - likely to appear
expected_issues=["type", "annotation"]

# Bad - too specific
expected_issues=["add type annotations to function parameters"]
```

### 2. Include Multiple Keywords

```python
# More robust - passes if ANY keyword matches
expected_issues=["SQL injection", "parameterized", "prepared statement"]
```

### 3. Test Your Test Cases

Run against the evaluator before committing:

```python
result = evaluator.evaluate(test_case)
print(f"Review: {result.review_text}")
print(f"Matched: {result.matched_issues}")
print(f"Missed: {result.missed_issues}")
```

### 4. Document the Expected Issue

```python
test_case = GoldenTestCase(
    id="shell-injection",
    file_path="cmd.py",
    code='''
# ISSUE: Using shell=True with user input allows command injection
subprocess.run(f"ls {user_dir}", shell=True)
''',
    expected_issues=["shell", "injection"],
    category="security",
)
```

## Organizing Test Cases

### By Category

```
tests/
  test_python_patterns.py
  test_typescript_patterns.py
  test_sql_patterns.py
  test_security_patterns.py
```

### By Severity

```
tests/
  test_critical_issues.py    # Must-fix
  test_warnings.py           # Should-fix
  test_suggestions.py        # Nice-to-fix
```

## Debugging Failed Tests

When a test fails:

```python
result = evaluator.evaluate(test_case)

if not result.passed:
    print("=== Review Text ===")
    print(result.review_text)
    print()
    print("=== Missed Issues ===")
    print(result.missed_issues)
```

Common causes:

1. **Keyword too specific** - The model uses different phrasing
2. **Issue too subtle** - The model doesn't catch it
3. **Wrong category** - The prompt doesn't focus on this type
