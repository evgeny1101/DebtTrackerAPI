# DebtTracker API

Python/FastAPI backend for [DebtTracker](https://github.com/ShAlexandra/DebtTracker) Android app.
Personal debt tracking with multi-user JWT authentication, transactional payment logic, and user isolation.

## Quick Start

```bash
mkdir data
docker compose up -d --build
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

Before deploying, generate a real JWT secret:
```bash
openssl rand -hex 32
# Set JWT_SECRET in .env or pass to docker compose
```

## Features

- JWT auth with access + refresh tokens (token rotation)
- Multi-user data isolation — each user sees only their own debts
- Atomic payment transactions: check → insert → deduct `currentAmount`
- Payment deletion restores `currentAmount`
- Debt editing with automatic `currentAmount` recalculation
- Rate limiting on login/register (5 req/min per IP)
- Structured logging (`LOG_LEVEL` env variable)
- 41 automated tests, Swagger auto-docs, Ruff linting

## Android App

This API serves the [DebtTracker Android app](https://github.com/ShAlexandra/DebtTracker) by [ShAlexandra](https://github.com/ShAlexandra).

## Tech Stack

**FastAPI** · **SQLAlchemy** · **SQLite** · **Alembic** · **Docker** · **JWT** · **bcrypt** · **slowapi** · **Ruff**

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `sqlite:///./debts.db` | Overridden in docker-compose to `/data/debts.db` |
| `JWT_SECRET` | `dev-secret-change-me` | Generate with `openssl rand -hex 32` for production |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose, `WARNING` for production |

## Project Structure

```
DebtTrackerAPI/
├── app/
│   ├── main.py              # FastAPI app: CORS, lifespan, routers, rate limiter
│   ├── models.py            # SQLAlchemy ORM: User, RefreshToken, Debt, Payment
│   ├── schemas.py           # Pydantic request/response models
│   ├── auth.py              # JWT encode/decode, bcrypt hash/verify
│   ├── routers/             # HTTP endpoints (auth, debts, payments)
│   └── crud/                # Business logic + DB queries + transactions
├── tests/                   # 41 pytest tests (auth, debts, payments)
├── alembic/                 # DB migrations
├── Dockerfile + docker-compose.yml
└── .opencode/               # OpenCode skills
```

## Testing

```bash
# Run test suite (inside container)
docker compose exec api pip install -q pytest httpx
docker compose exec api python -m pytest tests/ -v
```

41 tests covering auth, CRUD, payments, user isolation, and business logic.

## Linting

```bash
# Lint + format (inside container)
docker compose exec api ruff check --fix . && docker compose exec api ruff format .
```
