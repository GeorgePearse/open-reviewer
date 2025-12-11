# Contributing to Open Reviewer

Thank you for your interest in contributing to Open Reviewer! This document provides guidelines and conventions for contributing to the project.

## Python Typing Conventions

This project uses **strict static typing** throughout the Python codebase. We use Python 3.12+ type syntax and Pyright in strict mode for type checking.

### Core Principles

1. **100% Type Coverage**: All functions, methods, and class attributes must have type annotations
2. **No Implicit Any**: Avoid using `Any` unless absolutely necessary; prefer specific types or unions
3. **Explicit Return Types**: All functions must have explicit return type annotations (including `-> None`)
4. **Generic Types**: Use modern generic syntax (`list[str]`, `dict[str, int]`) instead of typing module imports

### Type Annotation Guidelines

#### Function Signatures

```python
# ✅ Good - fully typed
def process_data(items: list[str], config: dict[str, Any]) -> tuple[int, str]:
    return len(items), "processed"

# ❌ Bad - missing type hints
def process_data(items, config):
    return len(items), "processed"
```

#### Class Attributes

```python
# ✅ Good - typed attributes
class DataProcessor:
    name: str
    items: list[str]
    config: dict[str, Any]

    def __init__(self, name: str) -> None:
        self.name = name
        self.items = []
        self.config = {}

# ❌ Bad - untyped attributes
class DataProcessor:
    def __init__(self, name):
        self.name = name
        self.items = []
        self.config = {}
```

#### Optional Types

```python
# ✅ Good - explicit optional
def find_item(name: str) -> str | None:
    # Returns None if not found
    return database.get(name)

# ❌ Bad - implicit optional
def find_item(name: str) -> str:
    # This can return None but type doesn't reflect it
    return database.get(name)
```

#### Type Aliases

```python
# Define type aliases for complex types
JsonDict = dict[str, Any]
FilePathList = list[Path]
ChunkResults = list[dict[str, str | int | float]]

# Use them consistently
def parse_json(data: JsonDict) -> ChunkResults:
    ...
```

### Pyright Configuration

The project uses Pyright in strict mode with the following configuration in `pyproject.toml`:

```toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "strict"
reportMissingTypeStubs = false  # Don't complain about third-party stubs
```

### Common Patterns

#### Typing Imports from Dynamic Modules

When importing from modules that may not be available:

```python
# Use TYPE_CHECKING guard for import-time only types
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from some_optional_module import SomeType

# Use string literals in annotations
def process(data: "SomeType") -> None:
    ...
```

#### Typing Decorators and Context Managers

```python
from typing import Iterator
from contextlib import contextmanager

@contextmanager
def temporary_file(name: str) -> Iterator[Path]:
    path = Path(name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
```

### Type Checking in Development

Before committing, ensure your code passes type checking:

```bash
cd review_eval
uv run pyright
```

The pre-commit hook (via prek) will also run type checking automatically.

### Dealing with Type Errors

1. **Fix the type error** - This is the preferred approach
2. **Refactor the code** - Sometimes a type error indicates a design issue
3. **Use `cast()` sparingly** - Only when you're certain about the type:
   ```python
   from typing import cast

   # Use cast when you know more than the type checker
   result = cast(list[str], json.loads(data))  # If you're certain it's a list of strings
   ```
4. **Use `# type: ignore` as last resort** - Always add a comment explaining why:
   ```python
   import legacy_module  # type: ignore[import-not-found]  # Legacy module without stubs
   ```

### Protocol and ABC Usage

Prefer Protocols for structural typing over Abstract Base Classes:

```python
from typing import Protocol

# ✅ Good - Protocol for structural typing
class Collector(Protocol):
    def collect(self) -> dict[str, Any]: ...
    def validate(self) -> bool: ...

# Use it without inheritance
class MetricsCollector:  # No explicit inheritance needed
    def collect(self) -> dict[str, Any]:
        return {"metrics": []}

    def validate(self) -> bool:
        return True
```

### Testing Type Annotations

Type annotations are not just documentation - they're tested by the type checker. Ensure that:

1. Test files also have proper type annotations
2. Mock objects have correct types
3. Test fixtures are properly typed

```python
import pytest
from pathlib import Path

@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("threshold: 80")
    return config_file

def test_load_config(temp_config_file: Path) -> None:
    config = load_config(temp_config_file)
    assert config.threshold == 80
```

## Other Contributing Guidelines

### Code Style

- We use Ruff for formatting and linting
- Line length: 100 characters
- Use double quotes for strings
- Follow PEP 8 with the exceptions configured in `pyproject.toml`

### Testing

- Write tests for all new functionality
- Maintain test coverage above 80%
- Use pytest for testing
- Mark integration tests with `@pytest.mark.integration`

### Pull Request Process

1. Ensure all tests pass: `uv run pytest`
2. Run quality checks: `.github/scripts/code_quality_checks.sh`
3. Update documentation if needed
4. Create a clear PR description
5. Request review from maintainers

### Development Setup

```bash
# Clone the repository
git clone https://github.com/GeorgePearse/open-reviewer.git
cd open-reviewer/review_eval

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run type checking
uv run pyright

# Run all quality checks
../.github/scripts/code_quality_checks.sh
```