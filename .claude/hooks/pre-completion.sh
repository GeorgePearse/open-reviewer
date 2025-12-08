#!/bin/bash
# This hook runs before Claude Code marks a task as complete

set -e

echo "Running pre-completion quality checks..."

# Change to review_eval directory
cd review_eval

# Run the same checks as prek
echo "1/3 Formatting code..."
uv run ruff format .

echo "2/3 Linting code..."
uv run ruff check --fix .

echo "3/3 Type checking..."
uv run pyright

echo "✓ All quality checks passed!"
exit 0
