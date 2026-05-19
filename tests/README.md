# Tests

This project has four test tiers. Each has a specific role — don't mix them.

| Tier | Folder | What | Speed | Needs DB? |
|---|---|---|---|---|
| **Unit** | `tests/unit/` | Domain logic + use cases (mocked ports) | ⚡ Fast | No |
| **Contract** | `tests/contract/` | Adapter compliance with port ABCs | ⚡ Fast | No |
| **Integration** | `tests/integration/` | Real HTTP + real Postgres | 🐢 Slow | Yes |
| **Architecture** | `tests/architecture/` | Import boundary enforcement | ⚡ Fast | No |

---

## Before Running Tests

Unit, contract, and architecture tests read from `src/env/.env` by default (gitignored local file).
Make sure it exists and has valid values — the template is already there when you clone.

For **integration tests** you also need a running Postgres:
```bash
docker compose -f docker-compose.local.yml up -d
```

---

## Running Tests

### Unit Tests
```bash
# PowerShell
uv run pytest tests/unit/ -v

# WSL / bash
uv run pytest tests/unit/ -v
```

### Contract Tests
```bash
uv run pytest tests/contract/ -v
```

### Integration Tests
```bash
# Start Postgres first (once)
docker compose -f docker-compose.local.yml up -d

# PowerShell — override DB password to match docker-compose
$env:APP_ENV="test"; $env:DATABASE_PASSWORD="testpassword"
uv run pytest tests/integration/ -v

# WSL / bash
APP_ENV=test DATABASE_PASSWORD=testpassword uv run pytest tests/integration/ -v
```

### Architecture / Boundary Tests
```bash
uv run pytest tests/architecture/ -v

# Also run import-linter directly for a detailed contract report
uv run lint-imports
```

### All Tests + Coverage Report
```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
```
Coverage HTML report is generated in `htmlcov/index.html`.

---

## Coverage

Coverage is configured in `.coveragerc` (and mirrored in `pyproject.toml`).

```bash
# Run with XML output (used by SonarCloud in CI)
uv run pytest tests/unit/ --cov=src --cov-report=xml

# Run with terminal output
uv run pytest tests/unit/ --cov=src --cov-report=term-missing
```

Minimum threshold: **80%** on unit tests (enforced in CI).

---

## CI Behaviour

On every push/PR, GitHub Actions runs:

```
lint → typecheck → unit → contract → integration → architecture → security → sonar (main only)
```

Integration tests in CI spin up a real Postgres service container — no manual docker needed.

---

## Adding Tests for a New Feature

1. **Unit test** → `tests/unit/application/use_cases/test_<feature>_use_case.py`
   - Mock the outbound port with `AsyncMock`
   - Test all business rule branches

2. **Contract test** → `tests/contract/outbound/test_<feature>_repository_contract.py`
   - Inherit `<Feature>RepositoryContract` and provide a concrete repo fixture

3. **Integration test** → `tests/integration/inbound/http/test_<feature>_endpoints.py`
   - Use the `client` fixture from `conftest.py`
   - Test full HTTP round-trip

4. **No test needed in `tests/architecture/`** — boundary tests are global, not per-feature.
