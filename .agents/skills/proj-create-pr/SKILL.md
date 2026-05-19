---
name: create-pr
description: Creates a standardized Pull Request description and automates the PR creation process. Trigger this whenever the user asks to "create a PR", "make a pull request", or "draft a PR".
---

A skill to automatically analyze git changes and generate a high-quality, standardized Pull Request.

### Capture Intent
Before creating the PR, determine what changes are being made:
1. Run `git status` to see what is currently modified/staged.
2. Run `git diff` and `git diff --staged` to understand the actual code changes.
3. If the user hasn't provided a specific title or context, ask them for a brief 1-sentence summary of what this PR is meant to achieve before generating the full description.

### The PR Template
When you draft the PR, you MUST strictly follow this exact template structure. Do not skip any sections.

```markdown
# [Title: type(scope): description — Must follow Conventional Commits (e.g. feat: add login)]

## Video Demo
> *[Instruction: If UI changes were made, remind the user to insert a Loom link or MP4 here. If purely backend, put "N/A - Backend changes only".]*

## Summary
> *[Instruction: Write a 2-3 sentence high-level overview of why these changes were made and what problem they solve.]*

## Changes
> *[Instruction: Use a bulleted list to detail the specific logical changes made.]*
- Added X
- Fixed Y
- Updated Z

## Files Changed
> *[Instruction: List the most important files touched and a brief 3-5 word note on what changed in each.]*
- `path/to/file.py` - *added new handler*
- `path/to/other.py` - *updated validation logic*

## Future Enhancements
> *[Instruction: List any technical debt, edge cases, or follow-up work that was explicitly left out of this PR but should be addressed in the future.]*
```

### Execution Steps
1. Analyze the diffs to populate the "Summary", "Changes", and "Files Changed" sections.
2. Deduce "Future Enhancements" based on TODO comments in the diff, or simply leave a placeholder if none are obvious.
3. Present the drafted PR description to the user for review.
4. If the user approves, and the `gh` (GitHub CLI) is installed, offer to run `gh pr create --title "..." --body "..."` to open the PR for them automatically. Otherwise, instruct them to copy/paste the markdown into GitHub.
