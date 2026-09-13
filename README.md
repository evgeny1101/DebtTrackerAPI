# DebtTracker API

Python/FastAPI backend for [DebtTracker](https://github.com/ShAlexandra/DebtTracker) Android app.
Personal debt tracking with multi-user JWT authentication, transactional payment logic, and user isolation.

## Quick Start

```bash
mkdir data
# Container runs as non-root uid 1001 — make /data writable:
sudo chown 1001:1001 data
docker compose up -d --build
```

Dev only:
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

Before deploying, generate a real JWT secret and an unguessable API path prefix:
```bash
openssl rand -hex 32                                     # JWT_SECRET
openssl rand -base64 32 | tr '/+' '_-'                   # API_PATH_PREFIX (embed in the app)
# Set ENVIRONMENT=production plus above in .env
```

Production deployment (nginx TLS on `8443` with your ACME cert for the server IP):

```bash
docker compose --profile proxy up -d --build
# API: https://<server-ip>:8443/<API_PATH_PREFIX>/api/...
# Cert reload hook: certbot renew --deploy-hook "$(pwd)/reload-nginx.sh"
```
See [Deployment](#deployment-production) in AGENTS.md for the full production checklist.

## Features

- JWT auth with access + refresh tokens (token rotation)
- VK ID sign-in/sign-up (PKCE + `state` verified on the Android client)
- Multi-user data isolation — each user sees only their own debts
- Atomic payment transactions: check → insert → deduct `currentAmount`
- Payment deletion restores `currentAmount`
- Debt editing with automatic `currentAmount` recalculation
- Rate limiting on auth endpoints (login/register/refresh/vk 5 req/min, logout 10 req/min per IP)
- Refresh tokens stored as SHA-256 hashes (raw never persisted)
- Structured logging (`LOG_LEVEL` env variable)
- 75 automated tests, Swagger auto-docs, Ruff linting

## Android App

This API serves the [DebtTracker Android app](https://github.com/ShAlexandra/DebtTracker) by [ShAlexandra](https://github.com/ShAlexandra).

## Tech Stack

**FastAPI** · **SQLAlchemy** · **SQLite** · **Alembic** · **Docker** · **JWT** · **bcrypt** · **slowapi** · **httpx** · **Ruff**

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `sqlite:///./debts.db` | Overridden in docker-compose to `/data/debts.db` |
| `ENVIRONMENT` | `development` | `production` refuses to start on weak/missing config |
| `JWT_SECRET` | `dev-secret-change-me` | Generate with `openssl rand -hex 32`; production requires >= 32 chars |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose, `WARNING` for production |
| `CORS_ORIGINS` | (empty) | Comma-separated allowed origins; other origins rejected |
| `API_PATH_PREFIX` | (empty) | Unguessable prefix for all API routes; production requires >= 32 chars |
| `ENABLE_DOCS` | auto | `true` in dev, `false` in production; controls `/docs` and `/openapi.json` |
| `VK_CLIENT_ID` | (empty) | VK ID app client id (public app). Empty disables `/api/auth/vk` (returns 503) |
| `CERT_DIR` | `/root/cert` | Host dir with `ip/fullchain.pem` + `ip/privkey.pem` for nginx |

## Project Structure

```
DebtTrackerAPI/
├── app/
│   ├── main.py              # FastAPI app: CORS, lifespan, routers, rate limiter
│   ├── models.py            # SQLAlchemy ORM: User, RefreshToken, Debt, Payment
│   ├── schemas.py           # Pydantic request/response models
│   ├── auth.py              # JWT encode/decode, bcrypt hash/verify
│   ├── vk.py                # VK ID OAuth client (code exchange + user_info)
│   ├── routers/             # HTTP endpoints (auth, debts, payments)
│   └── crud/                # Business logic + DB queries + transactions
├── tests/                   # 75 pytest tests (auth, VK ID, debts, payments, config)
├── alembic/                 # DB migrations
├── Dockerfile + docker-compose.yml
└── .opencode/               # OpenCode skills
```

## Testing

```bash
# Run test suite (inside container)
docker compose exec api pip install -q -r requirements-dev.txt
docker compose exec api python -m pytest tests/ -v
```

75 tests covering auth (incl. VK ID), CRUD, payments, user isolation, and business logic.

## Linting

```bash
# Lint + format (inside container)
docker compose exec api ruff check --fix . && docker compose exec api ruff format .
```
