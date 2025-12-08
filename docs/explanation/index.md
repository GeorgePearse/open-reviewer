# Explanation

Understanding how Open Reviewer works and why it's designed this way.

## Core Concepts

<div class="grid cards" markdown>

-   :material-chart-bubble:{ .lg .middle } **Architecture**

    ---

    System architecture and component interactions

    [:octicons-arrow-right-24: Architecture](architecture.md)

-   :material-check-all:{ .lg .middle } **Multi-Model Consensus**

    ---

    Why consensus matters and how it works

    [:octicons-arrow-right-24: Consensus](multi-model-consensus.md)

-   :material-file-tree:{ .lg .middle } **Semantic Context**

    ---

    How semantic analysis enhances reviews

    [:octicons-arrow-right-24: Semantic](semantic-context.md)

-   :material-counter:{ .lg .middle } **Token Budgets**

    ---

    How context is allocated within token limits

    [:octicons-arrow-right-24: Budgets](token-budgets.md)

</div>

## Philosophy

Open Reviewer is built on these principles:

1. **Trust through consensus** - Multiple independent models agreeing provides higher confidence than any single model
2. **Measurable quality** - Golden test cases provide objective metrics for review quality
3. **Context awareness** - Reviews should understand the codebase, not just the changed lines
4. **Automation first** - Designed for CI/CD integration from day one
