# Getting Started

## Prerequisites

- Python 3.14+
- [UV](https://docs.astral.sh/uv/) installed
- Docker + Docker Compose (for integration tests)

## Setup

```bash
# Clone the repo
git clone https://github.com/your-org/hexagonal-backend-template.git
cd hexagonal-backend-template

# Install all dependencies (runtime + dev)
uv sync --group dev
```

The API will be available at `http://localhost:8000`.
- Swagger UI: `http://localhost:8000/docs`
- Health check: `GET http://localhost:8000/health`
- Ping: `POST http://localhost:8000/ping`

---

## Running the Dev Server

### PowerShell (Windows)
```powershell
$env:APP_ENV="dev"; $env:DATABASE_PASSWORD="localpass"; $env:SECRET_KEY="dev-secret"
uv run uvicorn app.infrastructure.main:app --reload --host 0.0.0.0 --port 8000
```

### WSL / bash / macOS
```bash
APP_ENV=dev DATABASE_PASSWORD=localpass SECRET_KEY=dev-secret \
  uv run uvicorn app.infrastructure.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Running Tests

### PowerShell (Windows)
```powershell
# Set test env once per terminal session
$env:APP_ENV="test"; $env:DATABASE_PASSWORD="x"; $env:SECRET_KEY="x"

uv run pytest tests/unit/ -v                         # unit tests
uv run pytest tests/contract/ -v                     # contract tests
uv run pytest tests/architecture/ -v                 # boundary tests
uv run pytest tests/ --cov=src --cov-report=term-missing  # all + coverage

# Integration tests (start Postgres first)
docker compose -f docker/docker-compose.local.yml up -d
$env:DATABASE_PASSWORD="testpassword"
uv run pytest tests/integration/ -v
```

### WSL / bash / macOS
```bash
APP_ENV=test DATABASE_PASSWORD=x SECRET_KEY=x uv run pytest tests/unit/ -v
APP_ENV=test DATABASE_PASSWORD=x SECRET_KEY=x uv run pytest tests/contract/ -v
APP_ENV=test DATABASE_PASSWORD=x SECRET_KEY=x uv run pytest tests/architecture/ -v
APP_ENV=test DATABASE_PASSWORD=x SECRET_KEY=x \
  uv run pytest tests/ --cov=src --cov-report=term-missing

# Integration tests
docker compose -f docker/docker-compose.local.yml up -d
APP_ENV=test DATABASE_PASSWORD=testpassword SECRET_KEY=x uv run pytest tests/integration/ -v
```

---

## Code Quality

Run in this **exact order** before every push (see [LOCAL_CI_GUIDE.md](./LOCAL_CI_GUIDE.md)):
```bash
uv run ruff format src/ tests/      # 1. format (must run BEFORE lint)
uv run ruff check src/ tests/ --fix # 2. lint
uv run mypy src/                    # 3. type check
uv run pytest tests/                # 4. full test suite
uv run bandit -r src/ -ll           # 5. security scan
uv run pip-audit                    # 6. CVE audit
```

---

## Environment Variables

Config is loaded from `src/env/{APP_ENV}.env` automatically.
Secrets (`DATABASE_PASSWORD`, `SECRET_KEY`) must always be injected at runtime — never stored in `.env` files.

See [environments.md](./environments.md) for the full config/secret split.

---

## Adding a New Domain Concept

1. Create entity + value objects in `src/app/domain/models/`
2. Create domain exceptions in `src/app/domain/exceptions/`
3. Define inbound port in `src/app/application/ports/inbound/`
4. Define outbound port in `src/app/application/ports/outbound/`
5. Implement use case in `src/app/application/use_cases/`
6. Implement repository in `src/app/infrastructure/adapters/outbound/persistence/`
7. Add router in `src/app/infrastructure/adapters/inbound/http/`
8. Wire everything in `src/app/infrastructure/config/container.py`
9. Add contract tests, unit tests, and integration tests
