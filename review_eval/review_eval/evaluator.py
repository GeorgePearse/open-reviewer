"""Core evaluation logic for testing Claude Code reviews."""

import anthropic

from review_eval.models import GoldenTestCase, ReviewResult


class ReviewEvaluator:
    """Evaluates Claude's review quality against golden test cases.

    This class sends code snippets to Claude for review and checks whether
    the expected anti-patterns are correctly identified.

    Attributes:
        client: Anthropic API client.
        prompt_context: System prompt providing review context.
        model: Claude model to use for evaluation.
    """

    def __init__(
        self,
        prompt_context: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """Initialize the evaluator.

        Args:
            prompt_context: System prompt with review instructions.
            model: Claude model ID to use.
        """
        self.client = anthropic.Anthropic()
        self.prompt_context = prompt_context
        self.model = model

    def evaluate(self, test_case: GoldenTestCase) -> ReviewResult:
        """Run Claude review on a test case and check for expected issues.

        Args:
            test_case: The golden test case to evaluate.

        Returns:
            ReviewResult with pass/fail status and details.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": f"Review this code for issues:\n\n```\n{test_case.code}\n```",
                }
            ],
            system=self.prompt_context,
        )

        review_text = response.content[0].text if response.content else ""
        review_text_lower = review_text.lower()

        matched = [issue for issue in test_case.expected_issues if issue.lower() in review_text_lower]
        missed = [issue for issue in test_case.expected_issues if issue.lower() not in review_text_lower]

        return ReviewResult(
            test_id=test_case.id,
            passed=len(missed) == 0,
            review_text=review_text,
            matched_issues=matched,
            missed_issues=missed,
        )
