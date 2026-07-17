# CyberArena

A hands-on cybersecurity training and simulation platform. CyberArena lets
security teams and students practice the full defensive lifecycle — attack
simulation, threat detection, incident response, threat hunting, and
reporting — in a safe, fully simulated environment.

> **Status:** Milestone 2 — authentication. Users can register, sign in,
> and access a protected dashboard. Domain modules (simulator, detection,
> incidents, hunting, reports) are scaffolded but not yet implemented.

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

Apply pending migrations (required before first run and after pulling
schema changes):

```bash
alembic upgrade head
```

Create a new migration after changing models:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Authentication

CyberArena uses session-based authentication with signed, HTTPOnly,
SameSite=Lax cookies (Secure flag in production). Passwords are hashed with
bcrypt via passlib; all state-changing forms carry CSRF tokens.

Session behavior is configured via environment variables (see
`.env.example`): `SECRET_KEY` signs the session cookie,
`SESSION_COOKIE_NAME` and `SESSION_MAX_AGE` control the cookie itself.

### Creating the first user

Run the app and register through the UI at http://localhost:8000/register —
new accounts get the `student` role. To create a user from the command line
instead:

```bash
python -c "
from app.core.database import SessionLocal
from app.auth.services import register_user
with SessionLocal() as db:
    user = register_user(db, 'admin', 'admin@example.com', 'a-strong-password')
    print('created', user.username, user.id)
"
```

### Routes

| Route        | Method    | Access        | Purpose                          |
| ------------ | --------- | ------------- | -------------------------------- |
| `/register`  | GET/POST  | anonymous     | Create an account                |
| `/login`     | GET/POST  | anonymous     | Sign in (username or email)      |
| `/logout`    | POST      | authenticated | Destroy the session              |
| `/dashboard` | GET       | authenticated | Account overview                 |

## Testing

```bash
pytest
```

## Documentation

See [docs/architecture.md](docs/architecture.md) for an overview of the
application architecture and conventions.

## License

For training and educational purposes.
