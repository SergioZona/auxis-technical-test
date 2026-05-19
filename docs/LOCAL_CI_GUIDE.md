# Local CI Checks Guide

Before pushing code to the repository, it's essential to run the same checks that GitHub Actions will run. This ensures you catch formatting issues, linting errors, type failures, and failing tests early—keeping the `main` branch green and avoiding "fix CI" commits.

Run these commands in this exact order to validate your changes:

## 1. Format Code (`ruff format`)
**Command**: `uv run ruff format src/ tests/`
**Importance**: Formats code to adhere strictly to PEP-8 and project conventions. Running this first prevents the linter from complaining about easily fixable spacing or styling issues. It automatically modifies your files.

## 2. Lint Code (`ruff check`)
**Command**: `uv run ruff check src/ tests/ --fix`
**Importance**: Analyzes your code for syntax errors, bad practices, unused imports, and security smells. The `--fix` flag will safely auto-correct many issues. If it outputs errors, you must fix them manually before proceeding. 

## 3. Type Checking (`mypy`)
**Command**: `uv run mypy src/`
**Importance**: Enforces static typing (Python 3.14). It catches critical runtime bugs (like passing a `str` instead of a `UUID`, or returning `None` unexpectedly) before the code ever executes.

## 4. Architecture & Unit Tests (`pytest`)
**Command**: `uv run pytest tests/`
**Importance**: Executes your unit, integration, and architecture boundary tests (`import-linter`). If this fails, either your logic is broken, or you've violated the Hexagonal Architecture (e.g., Domain importing Infrastructure).

## 5. Security Scanning (`bandit`)
**Command**: `uv run bandit -c pyproject.toml -r src/`
**Importance**: Scans the AST (Abstract Syntax Tree) for known Python security vulnerabilities (e.g., hardcoded passwords, unsafe `subprocess` usage, weak cryptography).

## 6. Dependency Audit (`pip-audit`)
**Command**: `uv run pip-audit`
**Importance**: Checks your locked dependencies (`uv.lock`) against a database of known CVEs (Common Vulnerabilities and Exposures). Ensures you aren't shipping vulnerable open-source packages to production.

---

### Pro-Tip: Chain them together
If you use a Bash-like terminal, you can string them together to fail fast:
```bash
uv run ruff format src/ tests/ && uv run ruff check src/ tests/ --fix && uv run mypy src/ && uv run pytest tests/ && uv run bandit -c pyproject.toml -r src/
```
