# Git & Commit Conventions

You must **ALWAYS** use [Conventional Commits](https://www.conventionalcommits.org/) when writing commit messages or Pull Request titles. 

This project uses **Release Please**. It relies entirely on these prefixes to automatically generate changelogs and bump semantic versions (`MAJOR.MINOR.PATCH`). If you don't use these prefixes, the automated release system will break.

## Allowed Types

| Prefix | Description | Effect on Version |
|---|---|---|
| `feat:` | A new feature | **MINOR** bump (e.g. 1.1.0 -> 1.2.0) |
| `fix:` | A bug fix | **PATCH** bump (e.g. 1.1.0 -> 1.1.1) |
| `docs:` | Documentation changes | None |
| `style:` | Formatting, whitespace, etc. | None |
| `refactor:`| Code change that neither fixes a bug nor adds a feature | None |
| `perf:` | Performance improvements | None |
| `test:` | Adding or fixing tests | None |
| `chore:` | Build process, dependency updates, tooling | None |

## Breaking Changes
If a commit introduces a breaking change (e.g., removing a field from an API response), append a `!` after the type/scope:
- `feat!: remove legacy item endpoints`
- This triggers a **MAJOR** bump (e.g., 1.1.0 -> 2.0.0).

## Examples
- `feat(auth): implement JWT token verification`
- `fix(db): resolve connection pool leak`
- `chore: bump uv dependencies`
