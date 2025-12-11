#!/bin/bash
# Comprehensive code quality checks for review_eval Python package
# Adapted from @anthropic/pal-mcp-server reference implementation
# Uses uv instead of pip/venv for dependency management

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REVIEW_EVAL_DIR="$PROJECT_ROOT/review_eval"

echo "=========================================="
echo "Code Quality Checks for review_eval"
echo "=========================================="
echo "Working directory: $REVIEW_EVAL_DIR"
echo ""

cd "$REVIEW_EVAL_DIR"

# Step 1: Install dependencies
echo "[1/6] Installing dependencies..."
uv sync --all-extras
echo "✓ Dependencies installed"
echo ""

# Step 2: Black formatting (check mode via Ruff)
echo "[2/6] Checking code formatting (Ruff format)..."
if uv run ruff format --check .; then
    echo "✓ Code formatting OK"
else
    echo "✗ Code formatting issues found"
    echo "  Run: cd review_eval && uv run ruff format ."
    exit 1
fi
echo ""

# Step 3: Ruff linting
echo "[3/6] Linting code (Ruff)..."
if uv run ruff check .; then
    echo "✓ No linting errors"
else
    echo "✗ Linting errors found"
    echo "  Run: cd review_eval && uv run ruff check --fix ."
    exit 1
fi
echo ""

# Step 4: isort import sorting (via Ruff)
echo "[4/6] Checking import ordering..."
if uv run ruff check --select I .; then
    echo "✓ Import ordering OK"
else
    echo "✗ Import ordering issues"
    echo "  Run: cd review_eval && uv run ruff check --select I --fix ."
    exit 1
fi
echo ""

# Step 5: Pyright type checking
echo "[5/6] Type checking (Pyright)..."
if uv run pyright; then
    echo "✓ Type checking passed"
else
    echo "✗ Type checking errors found"
    exit 1
fi
echo ""

# Step 6: Pytest unit tests (exclude integration tests)
echo "[6/6] Running unit tests (pytest)..."
if uv run pytest -v --tb=short -m "not integration"; then
    echo "✓ All unit tests passed"
else
    echo "✗ Test failures detected"
    exit 1
fi
echo ""

echo "=========================================="
echo "✓ All quality checks passed!"
echo "=========================================="
exit 0
