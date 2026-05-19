# ANTIGRAVITY — Project Context

> This file is loaded at the start of every Antigravity/AI agent session.
> Keep it up to date. It is the AI's map of this codebase.

## Project

**hexagonal-backend-template** — A production-ready Python hexagonal architecture template.

- **Language**: Python 3.14
- **Package manager**: UV
- **Framework**: FastAPI
- **DB**: PostgreSQL via SQLAlchemy async
- **DI**: dependency-injector (`container.py`)
- **Response format**: JSend

## Architecture

```
domain → application → infrastructure
```

- `domain/` — pure entities, value objects, exceptions (zero external deps)
- `application/ports/` — inbound + outbound ABCs
- `application/use_cases/` — business logic, implements inbound ports
- `infrastructure/adapters/inbound/` — FastAPI routers (HTTP)
- `infrastructure/adapters/outbound/` — SQLAlchemy Postgres repos
- `infrastructure/config/` — Settings (pydantic-settings) + Container (DI)

## Key Rules (from CONSTITUTION.md)

1. Domain never imports from application or infrastructure
2. Application never imports from infrastructure
3. All HTTP responses use JSend via `jsend.py`
4. Secrets are NEVER in `.env` files — only config
5. Every new adapter must pass its contract test
6. Use conventional commits

## Common Commands

### PowerShell (Windows)
```powershell
# Install
uv sync --group dev

# Dev server
$env:APP_ENV="dev"; $env:DATABASE_PASSWORD="localpass"; $env:SECRET_KEY="dev-secret"
uv run uvicorn app.infrastructure.main:app --reload --host 0.0.0.0 --port 8000

# Tests
$env:APP_ENV="test"; $env:DATABASE_PASSWORD="x"; $env:SECRET_KEY="x"
uv run pytest tests/unit/ -v
uv run pytest tests/contract/ -v
uv run pytest tests/integration/ -v
uv run pytest tests/architecture/ -v

# Quality
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/

# Security
uv run bandit -r src/ -ll
uv run pip-audit

# Local Postgres
docker compose -f docker-compose.local.yml up -d
```

### WSL / bash / macOS
```bash
# Install
uv sync --group dev

# Dev server
APP_ENV=dev DATABASE_PASSWORD=localpass SECRET_KEY=dev-secret \
  uv run uvicorn app.infrastructure.main:app --reload --host 0.0.0.0 --port 8000

# Tests
APP_ENV=test DATABASE_PASSWORD=x SECRET_KEY=x uv run pytest tests/unit/ -v
APP_ENV=test DATABASE_PASSWORD=x SECRET_KEY=x uv run pytest tests/contract/ -v
APP_ENV=test DATABASE_PASSWORD=x SECRET_KEY=x uv run pytest tests/integration/ -v
APP_ENV=test DATABASE_PASSWORD=x SECRET_KEY=x uv run pytest tests/architecture/ -v

# Quality
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/

# Security
uv run bandit -r src/ -ll
uv run pip-audit

# Local Postgres
docker compose -f docker-compose.local.yml up -d
```

## Env Files

`src/env/DEV.env`, `TEST.env`, `UAT.env`, `PROD.env` — config only.
Secrets `DATABASE_PASSWORD` and `SECRET_KEY` are always injected at runtime.

## Key Files

| File | Purpose |
|---|---|
| `src/app/domain/models/item.py` | Core entity example |
| `src/app/application/use_cases/item_use_case.py` | Use case example |
| `src/app/infrastructure/config/container.py` | DI wiring |
| `src/app/infrastructure/main.py` | FastAPI factory |
| `docs/CONSTITUTION.md` | Project law |
| `.antigravity/rules/` | Coding rules for AI agents |
