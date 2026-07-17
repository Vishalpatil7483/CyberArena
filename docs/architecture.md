# CyberArena Architecture

## Overview

CyberArena is a modular FastAPI application. Each domain (auth, simulator,
detection, incidents, hunting, reports, dashboard) lives in its own package
under `app/` and will expose its own router, services, and schemas as it is
implemented in later milestones.

## Layers

```
Request → Router (thin) → Service (business logic) → Models / DB
                ↓
            Template / JSON response
```

- **Routers** (`routes.py` in each module) validate input, call services,
  and shape the response. No business logic.
- **Services** (`app/services/`, or per-module `services.py`) contain the
  business logic and are plain, testable Python.
- **Models** (`app/models/`) are SQLAlchemy 2.0 declarative models sharing
  the `Base` from `app.core.database`. New model modules must be imported in
  `app/models/__init__.py` so Alembic autogenerate can see them.

## Core (`app/core/`)

| Module          | Responsibility                                              |
| --------------- | ----------------------------------------------------------- |
| `config.py`     | Pydantic Settings; per-environment classes (dev/prod/test)  |
| `database.py`   | Engine, `SessionLocal`, `Base`, `get_db` dependency         |
| `logging.py`    | Console + rotating file logging via `dictConfig`            |
| `errors.py`     | `AppError` hierarchy + centralized exception handlers       |
| `middleware.py` | Security headers middleware                                 |
| `templates.py`  | Shared Jinja2 environment                                   |
| `routes.py`     | Public pages (landing, health)                              |

## Configuration

Settings load from environment variables with a `.env` fallback
(`app/core/config.py`). `get_settings()` is cached; the `ENVIRONMENT`
variable selects `DevelopmentSettings`, `ProductionSettings`, or
`TestingSettings`. Production enforces a strong `SECRET_KEY` and disables
the interactive API docs.

## Error handling

Domain code raises `AppError` subclasses (`NotFoundError`, `ConflictError`,
`ValidationAppError`, …). Handlers in `app/core/errors.py` convert them to
JSON for API clients or rendered error pages for browser requests, and log
unexpected exceptions with tracebacks.

## Security headers

`SecurityHeadersMiddleware` adds `X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and a CSP
allowing only self plus the jsDelivr CDN (Bootstrap). HSTS is added in
production.

## Migrations

Alembic is configured in `alembic/env.py` to read the database URL from app
settings and target `Base.metadata`. Typical flow:

```bash
alembic revision --autogenerate -m "add <table>"
alembic upgrade head
```

## Adding a new module (later milestones)

1. Implement `routes.py`, `services.py`, `schemas.py`, and models inside the
   module package (e.g. `app/incidents/`).
2. Import new model modules in `app/models/__init__.py`.
3. Include the module router in `create_app()` (`app/main.py`).
4. Add tests under `tests/`.
