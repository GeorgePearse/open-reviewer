# Your First Evaluation

This tutorial walks you through running your first code review evaluation.

## Prerequisites

- Python 3.12 or later
- An Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))

## Step 1: Install Open Reviewer

Clone the repository and install dependencies:

```bash
git clone https://github.com/georgepearse/open-reviewer.git
cd open-reviewer/review_eval
```

Install with uv (recommended):

```bash
uv sync
```

Or with pip:

```bash
pip install -e .
```

## Step 2: Set Your API Key

Export your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## Step 3: Create a Test Case

Create a file `my_first_test.py`:

```python
from review_eval import ReviewEvaluator, GoldenTestCase

# Define a test case with known-bad code
test_case = GoldenTestCase(
    id="yaml-unsafe",
    file_path="example.py",
    code='''
import yaml

def load_config(path):
    with open(path) as f:
        return yaml.load(f)  # This is unsafe!
''',
    expected_issues=["safe_load"],  # We expect the review to mention safe_load
    category="security",
)

# Create an evaluator
evaluator = ReviewEvaluator(
    prompt_context="Review this Python code for security issues and best practices."
)

# Run the evaluation
result = evaluator.evaluate(test_case)

# Check the results
print(f"Test: {result.test_id}")
print(f"Passed: {result.passed}")
print(f"Matched Issues: {result.matched_issues}")
print(f"Missed Issues: {result.missed_issues}")
print()
print("Review Text:")
print(result.review_text)
```

## Step 4: Run the Evaluation

```bash
uv run python my_first_test.py
```

Expected output:

```
Test: yaml-unsafe
Passed: True
Matched Issues: ['safe_load']
Missed Issues: []

Review Text:
This code has a security vulnerability. The yaml.load() function is unsafe
because it can execute arbitrary Python code. You should use yaml.safe_load()
instead, which only loads basic Python objects...
```

## Understanding the Result

### GoldenTestCase

A test case contains:

- `id` - Unique identifier
- `code` - The code snippet to review
- `expected_issues` - Keywords that MUST appear in the review
- `category` - Type of test (security, python, typescript, sql)

### ReviewResult

The result contains:

- `passed` - True if all expected issues were found
- `matched_issues` - Which keywords were found
- `missed_issues` - Which keywords were NOT found
- `review_text` - The full review from the model

## Step 5: Try a Failing Test

Let's see what happens when the model misses something:

```python
# A more subtle issue
test_case = GoldenTestCase(
    id="psycopg2-deprecated",
    file_path="database.py",
    code='''
import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="mydb"
    )
''',
    expected_issues=["psycopg3", "deprecated"],  # Very specific keywords
    category="python",
)

result = evaluator.evaluate(test_case)
print(f"Passed: {result.passed}")
print(f"Missed: {result.missed_issues}")
```

If the model's review doesn't contain the exact keywords "psycopg3" and "deprecated", the test fails. This shows how golden tests work - they verify specific issues are mentioned.

## Step 6: Run the Built-in Tests

Open Reviewer includes 15+ pre-built test cases:

```bash
uv run pytest -v
```

This runs all tests in `tests/` against the review evaluator.

## Next Steps

Now that you've run your first evaluation:

1. [Set up multi-model consensus](multi-model-consensus.md) for higher confidence
2. [Add your own test cases](../how-to/add-test-cases.md)
3. [Explore the API reference](../reference/api/evaluators.md)

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

Make sure you've exported the key:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Rate limit exceeded"

Wait a moment and try again, or reduce the number of tests.

### Test fails but review looks correct

Check the `expected_issues` keywords. They must appear exactly in the review text. Try using more general keywords like "security" instead of specific phrases.
