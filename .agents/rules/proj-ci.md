# CI Pre-Push Rules

## MANDATORY: Run local CI before every push

Before pushing any commit to the remote, the AI agent MUST run all CI checks locally in this exact order and fix any issues before pushing. NEVER push code that fails any of these checks.

```powershell
# 1. Format first (fixes whitespace/style automatically)
uv run ruff format src/ tests/

# 2. Lint (detect bad imports, unused vars, code smells — fix before pushing)
uv run ruff check src/ tests/ --fix

# 3. Type check (must pass with 0 errors)
uv run mypy src/

# 4. Run full test suite (must pass 100%)
uv run pytest tests/

# 5. Security scan (must pass with no high/medium issues)
uv run bandit -r src/ -ll

# 6. Dependency CVE audit (must pass)
uv run pip-audit
```

## Rules

- Run steps 1 and 2 always together — format THEN lint.
- Fix ALL errors before pushing. Never suppress them.
- Never use `# noqa`, `# type: ignore`, `# nosec`, or any disable comment without explicit user approval.
- If a step fails, stop, fix the issue at the root cause, then restart the sequence from step 1.
- Do NOT push if any step exits with a non-zero return code.

## Why each step matters

| Step | Tool | What it catches |
|------|------|----------------|
| 1 | `ruff format` | Whitespace, blank lines, import order |
| 2 | `ruff check` | Bad practices, unused imports, type-checking violations |
| 3 | `mypy` | Runtime type mismatches caught statically |
| 4 | `pytest` | Logic bugs, broken contracts, boundary violations |
| 5 | `bandit` | Security vulnerabilities in source AST |
| 6 | `pip-audit` | CVEs in dependencies |
