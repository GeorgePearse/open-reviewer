# Contributing

Thank you for your interest in contributing to Open Reviewer!

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/GeorgePearse/open-reviewer.git
cd open-reviewer
```

### Set Up Development Environment

```bash
cd review_eval
uv sync --dev
```

### Run Tests

```bash
uv run pytest -v
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code
- Add tests
- Update documentation

### 3. Run Checks

```bash
# Run tests
uv run pytest -v

# Type checking (if configured)
uv run mypy review_eval

# Linting (if configured)
uv run ruff check .
```

### 4. Submit a Pull Request

1. Push your branch
2. Open a PR against `main`
3. Fill out the PR template
4. Wait for review

## Code Guidelines

### Python Style

- Use type hints on all public functions
- Follow PEP 8
- Maximum line length: 100 characters
- Use docstrings (Google style)

```python
def evaluate(self, test_case: GoldenTestCase) -> ReviewResult:
    """Evaluate a test case and return the result.

    Args:
        test_case: The test case to evaluate.

    Returns:
        ReviewResult with matched and missed issues.
    """
```

### Documentation

- Update docs when adding features
- Include code examples
- Use clear, concise language

### Tests

- Add tests for new functionality
- Maintain test coverage
- Use descriptive test names

```python
def test_multi_model_returns_consensus_issues():
    """MultiModelEvaluator should return consensus issues."""
    ...
```

## Types of Contributions

### Bug Fixes

1. Check existing issues first
2. Create an issue if not exists
3. Reference the issue in your PR

### New Features

1. Open an issue to discuss the feature
2. Get feedback before implementing
3. Document the feature thoroughly

### Documentation

- Fix typos and errors
- Improve explanations
- Add examples

### Test Cases

Add new golden test cases:

```python
GoldenTestCase(
    id="your-pattern-name",
    file_path="fixtures/your_pattern.py",
    code="...",
    expected_issues=["keyword1", "keyword2"],
    category="python",
)
```

## Project Structure

```
open-reviewer/
├── .github/
│   ├── workflows/      # GitHub Actions
│   ├── actions/        # Custom actions
│   └── scripts/        # Helper scripts
├── docs/               # Documentation (MkDocs)
├── review_eval/        # Main Python package
│   ├── review_eval/
│   │   ├── semantic/   # Semantic analysis
│   │   └── ...
│   └── tests/
└── mkdocs.yml
```

## Questions?

- Open an issue for questions
- Check existing issues and discussions
- Read the [documentation](https://georgepearse.github.io/open-reviewer/)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
