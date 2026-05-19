# Code Style Rules

## Ruff Configuration (see pyproject.toml)

- Line length: **88 chars**
- Target: `py314`
- Rules: `E, W, F, I, B, C4, UP, SIM, TCH, S`
- Tests may use `assert` (S101 ignored in `tests/`)

## Type Hints

- **Mandatory** on every function signature (including `__init__`)
- Use `X | None` not `Optional[X]`
- Use `list[X]` not `List[X]`
- No `Any` unless it's a boundary adapter receiving dynamic external data (e.g., serialization helpers). Must be documented with a comment explaining why.

## Naming

- Files: `snake_case.py`
- Classes: `PascalCase`
- Ports (interfaces): `PascalCasePort`
- Variables/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

## Docstrings

- Required on public classes and non-trivial public methods
- Use triple double quotes `"""`
- First line: one-sentence summary
- Do NOT repeat the function signature in the docstring

## Imports

- Absolute imports only (`from app.domain...`)
- No wildcard imports (`from module import *`)
- Group: stdlib → third-party → internal (Ruff/isort handles ordering)

## Disable / Ignore Policy

- `# noqa`, `# type: ignore`, `# nosec`, `# pragma: no cover` are **FORBIDDEN** unless the senior engineer explicitly approves them in review.
- Fix the underlying code issue. Never suppress the tool.
- The AI agent must never add any suppress comment autonomously.
