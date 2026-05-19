# Project Constitution
> *This document is the single source of truth for every developer and AI agent working on this codebase. It is law.*

---

## 1. Architecture Principles

This project follows **Hexagonal Architecture (Ports & Adapters)** mapped directly onto **Clean Architecture** principles. Both concepts are complementary: Hexagonal enforces the boundaries (ports/adapters), while Clean Architecture dictates the domain-centric dependency rule.

### Core Paradigms

1. **SOLID Principles**:
   - **S**ingle Responsibility: Each class/module has one reason to change.
   - **O**pen/Closed: Open for extension, closed for modification.
   - **L**iskov Substitution: Adapters must be perfectly substitutable for their Port interfaces.
   - **I**nterface Segregation: Keep Ports small and specific (e.g., `ItemReaderPort`, `ItemWriterPort` instead of a massive repository interface).
   - **D**ependency Inversion: High-level modules (Application) never depend on low-level modules (Infrastructure). Both depend on abstractions (Domain/Ports).

2. **Single Level of Abstraction Principle (SLAP)**:
   - Functions must operate at a single level of abstraction. Don't mix high-level business logic with low-level string manipulation or raw HTTP requests in the same method. Extract low-level details into private helper methods or adapters.

### Layer Diagram

```
┌─────────────────────────────────────────────────────────┐
│  INFRASTRUCTURE  (adapters + config)                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  APPLICATION  (ports + use cases)                 │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  DOMAIN  (models + exceptions)              │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Import Rules (enforced by import-linter + CI)

| Layer | May import from | Must NOT import from |
|---|---|---|
| `domain` | stdlib, nothing else | `application`, `infrastructure` |
| `application` | `domain`, stdlib | `infrastructure` |
| `infrastructure` | `domain`, `application`, third-party | — |

---

## 2. Naming Conventions

| Concept | Convention | Example |
|---|---|---|
| Files | `snake_case.py` | `item_use_case.py` |
| Classes | `PascalCase` | `ItemUseCase` |
| Interfaces (ports) | `PascalCasePort` | `ItemServicePort` |
| Variables / methods | `snake_case` | `find_by_id` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| Test files | `test_<subject>.py` | `test_item.py` |

---

## 3. API Conventions

- **Prefix**: all endpoints are versioned → `/api/v1/`
- **Health probes**: `/health` (liveness), `/ready` (readiness) — no version prefix
- **HTTP verbs**: `GET` read, `POST` create, `PATCH` partial update, `DELETE` remove
- **Response format**: **JSend** — always `{"status": "success|fail|error", "data|message": ...}`
- **Status codes**: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 404 Not Found, 409 Conflict, 500 Internal Error

### JSend Quick Reference

```json
// success
{"status": "success", "data": {...}}

// fail (client error — validation, not found)
{"status": "fail", "data": {"field": "error message"}}

// error (server error — unexpected)
{"status": "error", "message": "Something went wrong", "code": 500}
```

---

## 4. Testing Rules

| Tier | Location | What to test | May use I/O? |
|---|---|---|---|
| **Unit** | `tests/unit/` | Domain logic, use cases with mocked ports | No |
| **Contract** | `tests/contract/` | Port ABC compliance for every adapter | No |
| **Integration** | `tests/integration/` | Real HTTP + real DB | Yes (local Postgres) |
| **Architecture** | `tests/architecture/` | Import boundary enforcement | No |

- **Do not** put business logic assertions in integration tests.
- **Do not** use `unittest.mock` in integration tests.
- **Every** new adapter implementation must pass the corresponding contract test.

---

## 5. Git Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`
- **Branch naming**: `feat/<topic>`, `fix/<topic>`, `release/uat`, `hotfix/<topic>`
- **PRs**: must pass CI before merge; at least 1 review required
- **Version bumps**: handled automatically by Release Please on `main`

---

## 6. Code Style

- **Formatter + Linter**: Ruff (replaces black, isort, flake8)
- **Line length**: 88 characters
- **Type hints**: mandatory on all function signatures — use `dict[str, Any]` not bare `dict`
- **Docstrings**: required on all public classes and non-trivial methods
- **No bare `except`**: always catch specific exceptions

### Disable / Suppress Policy

`# noqa`, `# type: ignore`, `# nosec`, `# pragma: no cover` are **prohibited** unless explicitly approved by the senior engineer. Fix the root cause. Never silence the tool.

### Pre-Push CI Sequence (mandatory)

Every push must pass all of these locally first. See `docs/LOCAL_CI_GUIDE.md`:

```
uv run ruff format src/ tests/
uv run ruff check src/ tests/ --fix
uv run mypy src/
uv run pytest tests/
uv run bandit -r src/ -ll
uv run pip-audit
```

---

## 7. Error Handling

- Domain exceptions live in `domain/exceptions/`
- Use cases raise domain exceptions — never HTTP exceptions
- The global exception handler in `infrastructure/main.py` maps domain exceptions → JSend HTTP responses
- Routers must never catch raw exceptions — delegate to the global handler

---

## 8. Observability

- **Structured logging**: use `structlog` with JSON output in non-dev environments
- **Log levels**: DEBUG (dev only), INFO (default), WARNING (prod preferred)
- **Trace spans**: add OpenTelemetry spans at the use case layer for key operations
- **Never log secrets**: sanitize all log context

---

## 9. Security Rules

- No secrets in `.env` files, code, or logs
- Secrets are injected at runtime via Dokploy / GitHub Actions / server environment
- `bandit` and `pip-audit` must pass in CI — no exceptions
- Non-root Docker user for all production images

---

## 10. Domain Events

*(Placeholder for when you add event-driven behaviour)*

- Use cases emit domain events after successful state changes
- Events are plain dataclasses in `domain/events/`
- Outbound adapters consume events to trigger side-effects (emails, webhooks, queues)
- Events must not contain infrastructure types

---

## 11. Code Quality (SonarQube)

- **Local SonarQube**: Run `docker compose -f docker-compose.local.yml up -d sonarqube` to start the local instance at `http://localhost:9000`
- **Zero Bugs Policy**: No PR will be merged if SonarQube detects bugs, vulnerabilities, or security hotspots.
- **Cognitive Complexity**: Keep methods simple. SonarQube flags high cognitive complexity (too many nested `if`/`for` loops). Break down complex logic into private helper methods.
- **Code Smells**: Address code smells immediately to prevent technical debt.
- **Duplication**: Avoid code duplication. Extract shared logic into utility functions or base classes.
- **Test Coverage**: SonarQube gates require 80%+ test coverage. Always write tests for new code.
