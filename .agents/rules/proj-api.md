# API Conventions

## URL Structure

```
/health          → liveness probe (no version prefix)
/ready           → readiness probe (no version prefix)
/ping            → connectivity test (no version prefix)
/api/v1/<resource>   → all business endpoints
```

## HTTP Verbs

| Verb | Use |
|---|---|
| GET | Retrieve resource(s) |
| POST | Create new resource |
| PATCH | Partial update |
| PUT | Full replacement (rare) |
| DELETE | Remove resource |

## JSend Response Format

**Always use the `jsend.py` helpers. Never build raw response dicts in routers.**

```python
from app.infrastructure.adapters.inbound.http.jsend import success, fail, error

return success({"id": "...", "name": "..."})          # 2xx
return fail({"name": "Name is required"})              # 4xx
return error("Internal server error", code=500)        # 5xx
```

## Status Codes

| Code | When |
|---|---|
| 200 | Successful GET / PATCH |
| 201 | Successful POST (creation) |
| 204 | Successful DELETE (no body) |
| 400 | Validation error |
| 404 | Resource not found |
| 409 | Conflict (already exists) |
| 500 | Unhandled server error |

## Error Handling

- Domain exceptions are raised in use cases
- The global handler in `main.py` maps them to JSend HTTP responses
- Routers must NEVER catch exceptions — let the global handler do it
