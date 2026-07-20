# CyberArena

A hands-on cybersecurity training and simulation platform. CyberArena lets
security teams and students practice the full defensive lifecycle — attack
simulation, threat detection, incident response, threat hunting, and
reporting — in a safe, fully simulated environment.

> **Status:** Milestone 5 — profiles, leaderboards & achievements. Users
> have public profiles, a global points leaderboard, and automatically
> awarded achievements on top of the interactive lab engine. Remaining
> domain modules (simulator, detection, incidents, hunting, reports) are
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
| `/dashboard` | GET       | authenticated | Account overview + lab stats     |

## Labs & Challenges

The labs catalog covers six categories — Web Security, Network Security,
Cryptography, Linux, Digital Forensics, and Reverse Engineering — across
Easy/Medium/Hard difficulties. Each lab has an estimated duration and a
point value. Anyone can browse the catalog and lab details; starting and
completing labs requires an account. Per-user progress
(`not_started` → `in_progress` → `completed`) is tracked with one record
per user/lab, and the dashboard shows totals, completed and in-progress
counts, and a completion percentage.

### Seeding sample labs

After running migrations, load the 14 bundled sample labs and their
challenges:

```bash
python -m app.services.seed
```

The seeder matches labs by slug and challenges by (lab, title), so it is
safe to run repeatedly — nothing is duplicated or overwritten. Challenge
flags are hashed before insert; the database never stores plaintext flags.

### Challenge engine

Labs contain ordered challenges of three types — `flag`, `quiz`, and
`text`. Each challenge shows its description, point value, position in the
lab, a collapsed hint, and the user's attempt count. Signed-in users submit
answers through a CSRF-protected form and get immediate flash feedback
(Correct / Incorrect). Submitted flags are whitespace-trimmed and compared
case-sensitively against a bcrypt hash — plaintext flags are never stored
or compared. Points are awarded exactly once per challenge; repeat
submissions after completion never change attempts or points. When a
user's last remaining challenge in a lab is solved, the lab is
automatically marked completed (idempotently), and the dashboard shows
points earned plus solved/total challenge counts alongside the lab
statistics. Submitting to a challenge implicitly starts its lab.

Labs without challenges keep the manual "Mark completed" button from
Milestone 3; labs with challenges complete only through solving them.

### Lab routes

| Route                                   | Method | Access        | Purpose                       |
| --------------------------------------- | ------ | ------------- | ----------------------------- |
| `/labs`                                 | GET    | anonymous     | Browse the lab catalog        |
| `/labs/{slug}`                          | GET    | anonymous     | Lab details, challenge list   |
| `/labs/{slug}/start`                    | POST   | authenticated | Start a lab                   |
| `/labs/{slug}/complete`                 | POST   | authenticated | Complete a challenge-less lab |
| `/labs/{slug}/challenge/{id}`           | GET    | anonymous     | Challenge details             |
| `/labs/{slug}/challenge/{id}/submit`    | POST   | authenticated | Submit a flag                 |

## Profiles, Leaderboard & Achievements

Every account has a private profile at `/profile` (email, role, rank,
points, success rate, achievements, and the last 10 solved challenges) and
a public profile at `/users/{username}` that exposes only the username,
member-since date, rank, points, lab/challenge counts, and earned
achievements — never email addresses or internal IDs.

The global leaderboard at `/leaderboard` ranks active users by challenge
points (ties broken by challenge count, then older account first), 25 per
page, with the signed-in user highlighted. Inactive accounts are excluded
everywhere.

Achievements are awarded automatically and idempotently whenever a
challenge or lab is completed — 11 are seeded: First Blood, Explorer, six
category firsts (Web Apprentice, Cryptographer, Linux Explorer, Network
Analyst, Reverse Engineer, Forensics Rookie), and the 100/250/500 Points
Clubs. Achievement definitions live with the engine rules in
`app/services/achievements.py`, so seeded rows and awarding logic cannot
drift apart. The dashboard shows your rank, latest achievement, progress
toward the next points milestone, and a top-5 leaderboard preview.

### Profile & leaderboard routes

| Route                | Method | Access        | Purpose                        |
| -------------------- | ------ | ------------- | ------------------------------ |
| `/profile`           | GET    | authenticated | Own profile with private data  |
| `/users/{username}`  | GET    | anonymous     | Public profile                 |
| `/leaderboard`       | GET    | anonymous     | Global ranking (paginated)     |

Seeding (labs, challenges, achievements — idempotent):

```bash
python -m app.services.seed
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
