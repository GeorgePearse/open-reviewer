"""CLI interface for review evaluation and PR scoring."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from review_eval.collectors import (
    AIReviewCollector,
    CoverageCollector,
    StaticAnalysisCollector,
    TestResultCollector,
)
from review_eval.models import ScoringConfig
from review_eval.scoring_engine import ScoringEngine


async def score_command(args: argparse.Namespace) -> int:
    """Run PR scoring command.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for pass, 1 for fail).
    """
    # Load configuration
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Config file not found: {config_path}", file=sys.stderr)
            return 1
    else:
        # Use default config
        config = ScoringConfig(threshold=args.threshold)

    # Build collectors based on provided inputs
    collectors = []

    # Test results
    if args.junit:
        junit_path = Path(args.junit)
        collectors.append(TestResultCollector(junit_path, weight=config.weights.get("tests", 0.30)))

    # Coverage
    if args.coverage:
        coverage_path = Path(args.coverage)
        baseline = args.baseline_coverage if hasattr(args, "baseline_coverage") else None
        collectors.append(
            CoverageCollector(
                coverage_path,
                baseline_coverage=baseline,
                tolerance=config.tolerance.get("coverage_delta", 0.1),
                weight=config.weights.get("coverage", 0.20),
            )
        )

    # Static analysis
    if args.static_analysis:
        paths = args.static_analysis.split(",")
        ruff_path = Path(paths[0]) if len(paths) > 0 else None
        pyright_path = Path(paths[1]) if len(paths) > 1 else None

        collectors.append(
            StaticAnalysisCollector(
                repo_root=Path.cwd(),
                ruff_results_path=ruff_path,
                pyright_results_path=pyright_path,
                weight=config.weights.get("static_analysis", 0.20),
            )
        )

    # AI review
    if args.ai_review:
        ai_review_path = Path(args.ai_review)
        collectors.append(
            AIReviewCollector(
                review_results_path=ai_review_path,
                weight=config.weights.get("ai_review", 0.30),
            )
        )

    if not collectors:
        print(
            "Error: No metrics specified. Provide at least one of: --junit, --coverage, --static-analysis, --ai-review",
            file=sys.stderr,
        )
        return 1

    # Create scoring engine
    if args.config:
        engine = ScoringEngine.from_config_file(config_path, collectors)
    else:
        engine = ScoringEngine(config, collectors)

    # Calculate score
    result = await engine.calculate_score()

    # Output results
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        print(f"Score saved to: {output_path}")

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"PR Quality Score: {result.total_score:.1f}/100")
    print(f"Status: {result.status}")
    print(f"Threshold: {result.threshold}")
    print(f"{'=' * 60}\n")

    print("Breakdown:")
    for category, scoring_result in result.breakdown.items():
        status_icon = "✓" if scoring_result.error_message is None else "✗"
        print(
            f"  {status_icon} {category.value:20s}: {scoring_result.normalized_score:5.1f}/100 (weight: {scoring_result.weight:.0%})"
        )

    if result.blocking_factors:
        print(f"\n{chr(9888)} Blocking Factors:")  # Warning sign
        for factor in result.blocking_factors:
            print(f"  - {factor}")

    print()

    # Exit with appropriate code
    if args.fail_on_error and result.status == "FAIL":
        print("FAIL: Score below threshold", file=sys.stderr)
        return 1

    return 0


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Review evaluation and PR scoring tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Score a PR with all metrics
  uv run review-eval score \\
    --junit junit.xml \\
    --coverage coverage.xml \\
    --static-analysis ruff.json,pyright.json \\
    --threshold 80 \\
    --fail-on-error

  # Use config file
  uv run review-eval score \\
    --config reviewer.yaml \\
    --junit junit.xml \\
    --coverage coverage.xml \\
    --output pr-score.json \\
    --fail-on-error
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Score command
    score_parser = subparsers.add_parser("score", help="Calculate PR quality score")
    score_parser.add_argument("--config", "-c", help="Path to reviewer.yaml configuration file")
    score_parser.add_argument(
        "--junit", help="Path to JUnit XML file (e.g., junit.xml from pytest)"
    )
    score_parser.add_argument("--coverage", help="Path to Cobertura XML file (e.g., coverage.xml)")
    score_parser.add_argument(
        "--baseline-coverage",
        type=float,
        help="Baseline coverage percentage for delta calculation",
    )
    score_parser.add_argument(
        "--static-analysis",
        help="Comma-separated paths to ruff,pyright JSON results (or run tools if omitted)",
    )
    score_parser.add_argument(
        "--ai-review", help="Path to JSON file with AI review results (MultiModelResult[])"
    )
    score_parser.add_argument(
        "--threshold", type=float, default=80.0, help="Minimum passing score (default: 80)"
    )
    score_parser.add_argument("--output", "-o", help="Path to save JSON output (optional)")
    score_parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with code 1 if score is below threshold",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "score":
        return asyncio.run(score_command(args))

    return 0


if __name__ == "__main__":
    sys.exit(main())
