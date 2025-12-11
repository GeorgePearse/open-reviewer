# GitHub Integration Guide

Learn how to interact with Claude through GitHub issues and pull requests.

## Overview

Open Reviewer provides three ways to trigger Claude for automated code review and issue assistance:

1. **Automatic PR Reviews** - Claude automatically reviews all pull requests
2. **@claude Comments** - Mention @claude in any PR or issue comment
3. **Issue Labels** - Add the `claude` label to an issue for Claude to work on it

## Automatic PR Reviews

Claude automatically reviews all pull requests when the GitHub Action is properly configured. No manual trigger required.

**What happens:**
- Claude analyzes changed files in the PR
- Provides feedback on code quality, security, and best practices
- Posts review comments directly on the PR
- Uses repository-specific guidelines from `CLAUDE.md` files

**Setup:** See [Deploy GitHub Actions](../how-to/deploy-github-actions.md) for configuration details.

## @claude Comments

Mention `@claude` in any pull request or issue comment to get Claude's assistance.

### In Pull Requests

Use @claude to ask specific questions about the code changes:

```markdown
@claude can you review the security implications of this authentication change?
```

```markdown
@claude please suggest performance optimizations for the database queries in this PR
```

```markdown
@claude what are the potential edge cases I should test for this new feature?
```

### In Issues

Use @claude to get help with issue resolution:

```markdown
@claude please implement the feature described in this issue
```

```markdown
@claude can you investigate this bug and suggest a fix?
```

```markdown
@claude help me understand the root cause of this performance issue
```

### Best Practices for @claude Comments

**Be specific:** Provide clear, actionable requests
- ✅ "@claude review the SQL injection vulnerability in user.py:45"
- ❌ "@claude look at this"

**Include context:** Reference specific files, functions, or line numbers
- ✅ "@claude optimize the `process_data()` function for better memory usage"
- ✅ "@claude check lines 120-150 in auth.py for potential race conditions"

**Ask focused questions:** One clear task per comment
- ✅ "@claude add input validation to the login endpoint"
- ❌ "@claude fix everything and add tests and documentation"

**Use for implementation:** Claude can write code changes
- ✅ "@claude implement error handling for the API client"
- ✅ "@claude add unit tests for the new validation logic"

## Issue Labels

Add the `claude` label to any issue to have Claude work on it automatically.

**What happens:**
1. Claude reads the issue description and requirements
2. Analyzes the codebase to understand the context
3. Implements the requested changes
4. Creates a pull request with the solution

**Example workflow:**
1. Create an issue describing a bug or feature request
2. Add the `claude` label to the issue
3. Claude automatically starts working on it
4. Claude creates a PR with the implementation
5. Review and merge the PR when satisfied

### Issue Label Best Practices

**Write clear issue descriptions:**
```markdown
## Bug Report
The login form doesn't validate email formats properly.

## Steps to Reproduce
1. Enter "invalid-email" in the email field
2. Click submit
3. Form accepts invalid input

## Expected Behavior
Email validation should reject malformed addresses
```

**Include acceptance criteria:**
```markdown
## Acceptance Criteria
- [ ] Email validation rejects invalid formats
- [ ] Error message shows clear feedback
- [ ] Valid emails are accepted
- [ ] Tests cover edge cases
```

**Specify technical requirements:**
```markdown
## Technical Notes
- Use the existing validation library in `src/utils/validators.ts`
- Follow the error handling patterns in other form components
- Add unit tests to `tests/components/`
```

## Response Format

Claude will respond through GitHub comments with:

- **Progress updates** - Real-time todo lists showing work in progress
- **Implementation details** - Explanations of changes made
- **Pull request links** - When code changes are implemented
- **Review feedback** - Specific suggestions with file/line references

## Configuration

### Repository Setup

Create a `CLAUDE.md` file in your repository root with guidelines:

```markdown
# Code Review Guidelines

## Style
- Use TypeScript for new files
- Follow existing naming conventions
- Maximum function length: 50 lines

## Security
- Validate all user input
- Use parameterized queries
- No hardcoded secrets
```

### GitHub Action Configuration

Ensure your `.github/workflows/` includes the Claude action with appropriate triggers:

```yaml
on:
  pull_request:
  issue_comment:
    types: [created]
  issues:
    types: [labeled]

jobs:
  claude:
    if: |
      github.event_name == 'pull_request' ||
      contains(github.event.comment.body, '@claude') ||
      contains(github.event.label.name, 'claude')
```

## Limitations

- Claude cannot approve pull requests (security restriction)
- Cannot modify workflow files in `.github/workflows/`
- Works best with clear, specific instructions
- Large codebases may require focused requests

## Examples

### Code Review Request
```markdown
@claude please review this authentication middleware for security vulnerabilities:

Specifically check for:
- Session handling
- Input validation
- Authorization bypass
```

### Bug Fix Request
```markdown
@claude there's a memory leak in the image processing pipeline.

The issue appears in `src/processors/image.ts` around line 87 where we're not properly cleaning up canvas contexts.
```

### Feature Implementation
```markdown
@claude implement dark mode support:

Requirements:
- Toggle in user settings
- Persist preference in localStorage
- Apply to all UI components
- Smooth transitions between themes
```

## Troubleshooting

**Claude not responding?**
- Check the Actions tab for workflow errors
- Verify API keys are configured in repository secrets
- Ensure proper permissions are set (`pull-requests: write`)

**Responses are too generic?**
- Add more specific context in your request
- Reference exact files and line numbers
- Include relevant technical details

**Claude missed important context?**
- Update your `CLAUDE.md` with project-specific guidelines
- Provide more detailed issue descriptions
- Break complex requests into smaller, focused tasks

## Getting Started

1. Set up the GitHub Action following the [deployment guide](../how-to/deploy-github-actions.md)
2. Create a `CLAUDE.md` file with your project guidelines
3. Try a simple @claude comment on an existing PR
4. Create a test issue with the `claude` label
5. Review the results and refine your approach

Ready to get started? [Deploy GitHub Actions →](../how-to/deploy-github-actions.md)