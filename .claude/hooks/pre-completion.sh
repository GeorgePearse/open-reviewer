#!/bin/bash
# Enhanced pre-completion hook: runs quality checks only if review_eval/ was modified
# Uses the comprehensive code_quality_checks.sh script when available

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
QUALITY_SCRIPT="$PROJECT_ROOT/.github/scripts/code_quality_checks.sh"

echo "Running pre-completion quality checks..."

# Detect if review_eval/ was modified
if ! git diff --name-only HEAD 2>/dev/null | grep -q "^review_eval/"; then
    if ! git diff --cached --name-only HEAD 2>/dev/null | grep -q "^review_eval/"; then
        echo "✓ No review_eval/ changes detected, skipping Python checks"
        exit 0
    fi
fi

echo "review_eval/ changes detected, running quality checks..."

# Use comprehensive quality script if available
if [ -x "$QUALITY_SCRIPT" ]; then
    echo "Using comprehensive quality check script..."
    cd "$PROJECT_ROOT"
    "$QUALITY_SCRIPT"
else
    echo "Comprehensive script not found, falling back to basic checks..."
    cd "$PROJECT_ROOT/review_eval"

    # Fallback: run basic checks
    echo "[1/4] Formatting code..."
    uv run ruff format .

    echo "[2/4] Linting code..."
    uv run ruff check --fix .

    echo "[3/4] Type checking..."
    uv run pyright

    echo "[4/4] Running unit tests..."
    uv run pytest -v --tb=short -m "not integration"

    echo "✓ Basic quality checks passed!"
fi

exit 0
