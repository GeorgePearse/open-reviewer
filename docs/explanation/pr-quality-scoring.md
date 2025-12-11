# PR Quality Scoring Architecture

This document explains the design decisions and architecture behind the PR Quality Gate scoring system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    PR Quality Gate                       │
│                   (.github/workflows/                    │
│                     pr-gate.yml)                         │
└─────────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐     ┌────▼────┐     ┌────▼────┐
    │  Tests  │     │Coverage │     │ Static  │
    │ (pytest)│     │(cov.py) │     │Analysis │
    └────┬────┘     └────┬────┘     └────┬────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
                   ┌──────▼──────┐
                   │   Scoring   │
                   │   Engine    │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ PR Comment  │
                   │  + Status   │
                   └─────────────┘
```

## The Hybrid Deduction Model

### Why Not Pure Weighted Average?

A pure weighted average has a critical flaw: high scores in less critical areas can mask serious issues.

**Example Problem**:

```
Tests: 100 × 0.30 = 30
Coverage: 100 × 0.20 = 20
Static Analysis: 100 × 0.20 = 20
Security: 0 × 0.30 = 0 (SQL injection found!)
───────────────────────────
Total: 70/100 (PASS at 65 threshold)
```

This PR would pass despite having a security vulnerability!

### The Solution: Deduction Model

```
Score = Σ(CategoryScore × Weight) - CriticalPenalties
```

**With Critical Penalties**:

```
Weighted Sum: 70
Security Penalty: -100
───────────────────────────
Total: max(0, -30) = 0 (FAIL)
```

This ensures critical issues always block merges, regardless of other metrics.

### Penalty Configuration

From `.github/reviewer-gate.yaml`:

```yaml
scoring:
  critical_penalties:
    security_vulnerability: 100  # Immediate fail
    critical_test_failure: 50    # All tests failing
```

## Normalization Strategies

### Test Pass Rate: Linear

**Formula**: `(passed / total) × 100`

**Rationale**: Test results are binary - either tests pass or they don't. Linear mapping is appropriate.

**Example**:

- 40/40 tests pass → 100 score
- 38/40 tests pass → 95 score
- 0/40 tests pass → 0 score (+ penalty)

### Coverage Delta: Sigmoid

**Formula**:

```python
score = 50 + 50 × tanh(delta / 2.5)

# Examples:
delta = 0%  → score = 50
delta = +5% → score = 100
delta = -5% → score = 0
```

**Rationale**: Small coverage changes are noisy due to mathematical rounding. The sigmoid curve:

1. **Neutral at 0**: No change = 50 points (neutral)
2. **Smooth transitions**: Avoids harsh cliffs
3. **Tolerant of noise**: Small drops (<0.1%) ignored via tolerance threshold

**Why This Matters**:

Consider a small PR adding 10 lines of code with 100% test coverage. If the baseline is 85% and the new overall coverage is 84.95%, a linear model would heavily penalize this despite perfect testing. The sigmoid model treats this as neutral.

### Static Analysis: Exponential Decay

**Formula**:

```python
if errors == 0:
    score = 100
elif errors <= 5:
    score = 80
else:
    score = 80 × exp(-0.05 × (errors - 5))
```

**Rationale**: The impact of linting errors is not linear:

- **0 errors**: Perfect (100)
- **1-5 errors**: Minor issues (80) - might be acceptable
- **5+ errors**: Exponential decay - many errors indicate systemic problems

**Visual Curve**:

```
100 ┤●
 80 ┤─────●●●●●
 60 ┤          ●●
 40 ┤            ●●●
 20 ┤               ●●●●
  0 ┤                   ●●●●●→
    0  5 10 15 20 25 30 35 40
           Error Count
```

## Tolerance Thresholds

### The Coverage Noise Problem

**Scenario**: A PR adds 5 lines of code with 100% test coverage.

```
Before: 1000 lines, 850 covered (85%)
After:  1005 lines, 855 covered (85.07%)

Mathematical Coverage: 85.07%
Baseline: 85%
Delta: +0.07%
```

With strict scoring, this tiny change might trigger false positives.

### Solution: Tolerance Threshold

```yaml
tolerance:
  coverage_delta: 0.1  # Ignore changes < 0.1%
```

Changes within ±0.1% are treated as "no change" (50 score).

## Two-Layer Enforcement

### Layer 1: Local Prek Hooks

**Purpose**: Instant feedback for developers

**Tools**: Ruff formatter, ruff linter, pyright

**Timing**: On `git commit`

**Bypass**: Can use `--no-verify` (emergency escape)

**Advantages**:

- Fast (< 5 seconds)
- Catches issues before pushing
- Iterative feedback loop

### Layer 2: CI Enforcement

**Purpose**: Authoritative quality gate

**Tools**: Same as local (ensures consistency)

**Timing**: On PR open/update

**Bypass**: Cannot be bypassed

**Advantages**:

- Catches bypassed local hooks
- Runs all tests (not just local subset)
- Enforces baseline coverage comparison

### Why Both Layers?

| Scenario | Local Hook | CI Gate |
|----------|------------|---------|
| Developer commits clean code | ✅ Passes | ✅ Passes |
| Developer bypasses with `--no-verify` | ⚠️ Bypassed | ❌ Blocks |
| Baseline coverage decreases on main | ✅ Passes | ❌ Detects |
| Flaky test passes locally, fails in CI | ✅ Passes | ❌ Detects |

The two layers complement each other for comprehensive enforcement.

## Collector Architecture

### Pipeline Pattern

```python
class MetricCollector(ABC):
    @abstractmethod
    async def collect(self) -> ScoringResult:
        pass
```

**Benefits**:

1. **Pluggable**: Add new metrics without changing scoring engine
2. **Parallel**: Run all collectors concurrently (`asyncio.gather`)
3. **Isolated**: Each collector handles its own errors gracefully

### Four Collectors

1. **TestResultCollector**: Parses JUnit XML
2. **CoverageCollector**: Parses Cobertura XML, compares to baseline
3. **StaticAnalysisCollector**: Runs ruff + pyright programmatically
4. **AIReviewCollector**: Aggregates multi-model consensus (future)

### Graceful Degradation

If a collector fails:

```python
try:
    score = await collector.collect()
except Exception as e:
    score = ScoringResult(
        category=collector.category,
        raw_value=0,
        normalized_score=0,
        error_message=str(e)
    )
```

The scoring engine continues with reduced weight, rather than crashing.

## Configuration Philosophy

### Why YAML?

**Rationale**: Different projects have different priorities.

**Examples**:

**Security-critical project**:

```yaml
weights:
  tests: 0.25
  coverage: 0.15
  static_analysis: 0.20
  ai_review: 0.40  # Emphasize security review
```

**Legacy project**:

```yaml
threshold: 60  # Lower bar initially
weights:
  tests: 0.50  # Focus on test improvement
  coverage: 0.05  # De-emphasize coverage
  static_analysis: 0.45
```

**Fast-moving startup**:

```yaml
threshold: 70
weights:
  tests: 0.60  # Shipping velocity, but test quality
  coverage: 0.10
  static_analysis: 0.30
```

## Standard Formats

### Why JUnit XML and Cobertura?

**Rationale**: These are industry standards supported by all major test runners.

**Benefits**:

- Works with pytest, unittest, nose, etc.
- Works with coverage.py, codecov, etc.
- Language-agnostic (can extend to JS, Go, Rust)
- No vendor lock-in

### Parsing Robustness

All parsers include extensive error handling:

```python
try:
    tree = ET.parse(junit_path)
except ET.ParseError:
    # Graceful degradation
    return default_result()
```

Integration tests verify parsing with real artifacts from different test runners.

## Future Enhancements

### AI Review Integration

When the AI review collector is connected:

```yaml
weights:
  tests: 0.30
  coverage: 0.20
  static_analysis: 0.20
  ai_review: 0.30  # Newly enabled
```

AI review will aggregate `MultiModelResult` findings from the existing review.yml workflow, counting consensus issues by severity.

### Custom Metrics

The pipeline pattern allows easy extension:

```python
class ComplexityCollector(MetricCollector):
    async def collect(self) -> ScoringResult:
        # Calculate cyclomatic complexity
        score = calculate_complexity(files)
        return self._create_result(
            raw_value=score,
            normalized_score=normalize(score),
            details={"max_complexity": max_val}
        )
```

## Related Documentation

- [How-to: Configure PR Quality Gate](../how-to/pr-quality-gate.md)
- [Reference: CLI Commands](../reference/cli.md)
- [Architecture Overview](./architecture.md)
