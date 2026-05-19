# Testing Rules

## Test Tiers

| Tier | Folder | Rule |
|---|---|---|
| Unit | `tests/unit/` | Zero I/O. Mock all ports. Fast. |
| Contract | `tests/contract/` | Verify adapters satisfy port ABCs. No real DB. |
| Integration | `tests/integration/` | Real HTTP client + real Postgres (docker-up). |
| Architecture | `tests/architecture/` | Import boundary enforcement via import-linter. |

## Rules

1. Unit tests must use `unittest.mock.AsyncMock` for outbound ports
2. Never assert HTTP responses in unit tests (that's integration territory)
3. Every concrete repository implementation must pass `ItemRepositoryContract`
4. Architecture tests must run `lint-imports` as part of CI
5. `pytest-asyncio` with `asyncio_mode = "auto"` — no need for `@pytest.mark.asyncio`
6. Fixtures in `tests/conftest.py` are shared — don't duplicate them

## Naming

- Test files: `test_<subject>.py`
- Test functions: `test_<what>_<expected_outcome>`
- Example: `test_get_item_raises_when_not_found`

## Coverage

- Unit test coverage threshold: **80%** (enforced in CI)
- Coverage config in `pyproject.toml [tool.coverage]`
