# CyberArena

A hands-on cybersecurity training and simulation platform. CyberArena lets
security teams and students practice the full defensive lifecycle — attack
simulation, threat detection, incident response, threat hunting, and
reporting — in a safe, fully simulated environment.

> **Status:** Milestone 1 — project foundation. Domain modules (auth,
> simulator, detection, incidents, hunting, reports, dashboard) are
> scaffolded but not yet implemented.

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic Settings
- **Frontend:** Jinja2 templates, Bootstrap 5, Bootstrap Icons
- **Database:** SQLite (development), PostgreSQL (production)
- **Deployment:** Docker, docker-compose

## Project Structure

```
CyberArena/
├── app/
│   ├── main.py           # Application factory / ASGI entrypoint
│   ├── core/             # Config, database, logging, errors, middleware
│   ├── models/           # SQLAlchemy ORM models
│   ├── services/         # Business logic (routes stay thin)
│   ├── auth/             # Authentication (future milestone)
│   ├── dashboard/        # Security dashboard (future milestone)
│   ├── simulator/        # Attack simulation (future milestone)
│   ├── detection/        # Threat detection (future milestone)
│   ├── incidents/        # Incident response (future milestone)
│   ├── hunting/          # Threat hunting (future milestone)
│   ├── reports/          # Reporting (future milestone)
│   ├── static/           # CSS, JS, images
│   └── templates/        # Jinja2 templates
├── alembic/              # Database migrations
├── tests/                # Test suite
├── docs/                 # Documentation
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Getting Started

### Local development

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 3. Configure environment
cp .env.example .env             # edit values as needed

# 4. Run the application
uvicorn app.main:app --reload
```

Open http://localhost:8000 — the landing page should load.
API docs (development only): http://localhost:8000/docs

### Docker

```bash
cp .env.example .env
# set a strong SECRET_KEY in .env (required in production):
#   python -c "import secrets; print(secrets.token_hex(32))"
docker compose up --build
```

This starts the app on port 8000 with a PostgreSQL 16 database.

## Configuration

All configuration is environment-based (12-factor). See `.env.example` for
the full list. Key variables:

| Variable       | Default                      | Description                              |
| -------------- | ---------------------------- | ---------------------------------------- |
| `ENVIRONMENT`  | `development`                | `development`, `production`, `testing`   |
| `SECRET_KEY`   | `change-me`                  | Must be set to a strong value in prod    |
| `DATABASE_URL` | `sqlite:///./cyberarena.db`  | SQLAlchemy database URL                  |
| `LOG_LEVEL`    | `INFO`                       | Logging verbosity                        |

In production (`ENVIRONMENT=production`):
- API docs are disabled
- `SECRET_KEY` is validated (startup fails on a weak/default key)
- HSTS is enabled alongside the other security headers

## Database Migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Testing

```bash
pytest
```

## Documentation

See [docs/architecture.md](docs/architecture.md) for an overview of the
application architecture and conventions.

## License

For training and educational purposes.
