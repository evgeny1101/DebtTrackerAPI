# DebtTracker API

Python/FastAPI backend for the DebtTracker Android app — personal debt tracking with multi-user support, JWT authentication, and transactional business logic.

**Stack**: FastAPI + SQLAlchemy + SQLite + Alembic + Docker
**API format**: JSON, all field names camelCase (matching Android Room entities)

---

## Quick Start

```bash
mkdir data
# Container runs as non-root uid 1001 — make /data writable on a Linux host:
# sudo chown 1001:1001 data
docker compose up -d --build
```

Dev only: API on `http://localhost:8000`, Swagger UI `http://localhost:8000/docs`, Health `http://localhost:8000/health`.

Production deployment (TLS + unguessable path prefix, see [Deployment](#deployment-production)):

```bash
docker compose --profile proxy up -d --build
```
API: `https://<server-ip>:8443/<API_PATH_PREFIX>/api/...`

Before deploying, generate a real JWT secret:
```bash
openssl rand -hex 32
# Set JWT_SECRET in .env or pass to docker compose
```

---

## Commands

| Command | Purpose |
|---------|---------|
| `docker compose up -d --build` | Build image + start container |
| `docker compose down` | Stop container |
| `docker compose logs -f` | Follow logs |
| `docker compose exec api alembic revision --autogenerate -m "..."` | Generate new migration |
| `docker compose exec api alembic upgrade head` | Apply migrations manually |
| `docker compose exec api pip install -r requirements-dev.txt` | Install dev deps (pytest, ruff, httpx) once |
| `docker compose exec api python -m pytest tests/ -v` | Run test suite (75 tests) |
| `docker compose exec api python -m ruff check .` | Lint all Python files |
| `docker compose exec api python -m ruff check --fix .` | Auto-fix lint issues |
| `docker compose exec api python -m ruff format --check .` | Check formatting |
| `docker compose exec api python -m ruff format .` | Auto-format all Python files |

> Note: inside the container use `python -m ruff` — dev deps install to user-site (`~/.local/bin`), which is not on `PATH` for non-login `docker compose exec`.

Migrations run automatically on container start via `entrypoint.sh` — no manual steps needed for schema creation.

---

## Project Structure

```
DebtTrackerAPI/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app: CORS, lifespan, routers, rate limiter
│   ├── config.py            # ENV vars: DATABASE_URL, JWT_SECRET, expirations
│   ├── database.py          # SQLAlchemy engine, SessionLocal, Base
│   ├── models.py            # User, RefreshToken, Debt, Payment (camelCase columns)
│   ├── schemas.py           # Pydantic request/response models
│   ├── auth.py              # JWT encode/decode, bcrypt hash/verify
│   ├── vk.py                # VK ID OAuth client (code exchange + user_info)
│   ├── limiter.py           # slowapi limiter instance
│   ├── dependencies.py      # get_db (yield session), get_current_user (Bearer → User)
│   ├── crud/
│   │   ├── __init__.py
│   │   ├── debts.py         # CRUD + update recalculation, delete cascade
│   │   └── payments.py      # Atomic record (check→insert→deduct) and delete (restore)
│   └── routers/
│       ├── __init__.py
│       ├── auth.py          # POST /register, /login, /refresh, /logout, /vk
│       ├── debts.py         # /api/debts/* — 8 endpoints
│       └── payments.py      # /api/debts/:id/payments/*, /api/payments
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Fixtures: temp SQLite DB, TestClient, disable slowapi
│   ├── test_auth.py          # 19 tests: register, login, refresh, logout, 401/409
│   ├── test_vk.py            # 22 tests: VK sign-in, profile sync, migration 003
│   ├── test_debts.py         # 17 tests: CRUD, active filter, reminders, recalc
│   ├── test_payments.py      # 11 tests: record, delete, restore, 400 when fully paid
│   └── test_config.py        # 6 tests: production config validation
├── alembic/
│   ├── env.py               # Overrides DATABASE_URL from app.config
│   ├── script.py.mako
│   └── versions/
│       ├── 001_initial.py   # users, refresh_tokens, debts, payments
│       ├── 002_reset_refresh_tokens.py  # reset sessions (tokens now hashed)
│       └── 003_vk_id.py     # users: vkId/email/fullName, passwordHash nullable
├── alembic.ini
├── bruno/                       # Manual API test collection (49 requests, dev env)
├── Dockerfile               # python:3.12-slim, non-root appuser, PYTHONPATH=/app
├── docker-compose.yml       # api (127.0.0.1:8000) + nginx profile `proxy` (8443)
├── nginx/
│   └── nginx.conf           # TLS termination: 8443, cert /certs/ip/*, proxy to api
├── reload-nginx.sh          # certbot/acme.sh deploy-hook → nginx -s reload
├── entrypoint.sh             # alembic upgrade head → uvicorn (body limit 1 MB)
├── requirements.txt         # Pinned prod deps, no dev tools
├── requirements-dev.txt     # + ruff, pytest, httpx, pip-audit
├── pyproject.toml
├── .dockerignore             # Excludes __pycache__, .venv, .env, .git, data/
├── .gitignore
└── .env.example
```

---

## Architecture Layers

```
Request → Router (validates with Pydantic, extracts current_user from JWT)
        → CRUD (business logic, DB queries, SQLAlchemy session)
        → Models (SQLAlchemy ORM on top of SQLite)
```

**Key rule**: Routers are thin — only HTTP concerns. All logic lives in `app/crud/`.

---

## Conventions

| Aspect | Convention |
|--------|-----------|
| JSON field names | camelCase: `initialAmount`, `currentAmount`, `debtId`, `dateMillis`, `tokenType` |
| Python identifiers | snake_case: `current_user`, `debt_id`, `user_id` |
| DB column names | camelCase (match Android Room entities): `userId`, `debtId`, `createdAt` |
| Debt type enum | `"I_OWE"` (я должен) or `"OWE_ME"` (мне должны) |
| Timestamps | `int`, milliseconds since Unix epoch (`int(time.time() * 1000)`) |
| Amounts | `int` / `BigInteger`, no floats |
| Error format | `{"detail": "message"}` — FastAPI default |
| HTTP status codes | 201 (created), 204 (no content), 400 (bad request), 401 (unauthorized), 404 (not found), 409 (conflict), 502 (VK upstream failure) |
| Linting | Run `python -m ruff check . && python -m ruff format --check .` inside the container before every commit. Zero errors required |

---

## Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `sqlite:///./debts.db` | Overridden to `sqlite:////data/debts.db` in docker-compose |
| `ENVIRONMENT` | `development` | `production` enables fail-fast checks (JWT_SECRET strength, etc.) |
| `JWT_SECRET` | `dev-secret-change-me` | Generate with `openssl rand -hex 32`; production refuses to start unless it's a strong random value (>= 32 chars) |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose, `WARNING` for production |
| `CORS_ORIGINS` | (empty) | Comma-separated allowed origins; requests from other origins are rejected |
| `API_PATH_PREFIX` | (empty) | Unguessable base path for all API routes (e.g. `openssl rand -base64 32`). Production requires >= 32 chars; embed it in the mobile app at build time |
| `ENABLE_DOCS` | auto | `true` in dev, `false` in production by default; controls `/docs`, `/redoc`, `/openapi.json` |
| `VK_CLIENT_ID` | (empty) | VK ID app client id (public app). Empty disables `/api/auth/vk` (returns 503) |
| `CERT_DIR` | `/root/cert` | Host dir with `ip/fullchain.pem` + `ip/privkey.pem`, mounted into nginx (proxy profile) |

---

## API Endpoints

> All routes below are served under `<API_PATH_PREFIX>` in production
> (e.g. `/xKJ3…Tz8/api/auth/register`). Requests to the bare `/api/...` paths are not routed.

### Auth (no authentication required except /logout)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Register (username, password) → tokens. Rate-limited: 5/min |
| `POST` | `/api/auth/login` | Login → accessToken + refreshToken. Rate-limited: 5/min |
| `POST` | `/api/auth/refresh` | Exchange refreshToken → new pair (old token invalidated) |
| `POST` | `/api/auth/logout` | Invalidate refreshToken. Requires Bearer token |
| `POST` | `/api/auth/vk` | VK ID sign-in/sign-up. Body: `code`, `redirectUri`, `codeVerifier`, `deviceId`, `state?`. Rate-limited: 5/min |

### Debts (Bearer token required)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/debts` | List all debts. Query `?active=true` for `currentAmount != 0` |
| `GET` | `/api/debts/:id` | Get single debt (own debts only, 404 if not found) |
| `GET` | `/api/debts/with-reminders` | Debts with `reminderIntervalDays IS NOT NULL` |
| `POST` | `/api/debts` | Create debt. Body: `name`, `debtType`, `initialAmount`, `createdAt?`, `reminderIntervalDays?` |
| `PUT` | `/api/debts/:id` | Full edit. Body: `name`, `initialAmount`, `createdAt?`, `reminderIntervalDays?`. Recalculates `currentAmount` |
| `PATCH` | `/api/debts/:id/current-amount` | Update only `currentAmount`. Body: `amount` |
| `PATCH` | `/api/debts/:id/reminder-timestamp` | Update `lastReminderTimestamp`. Body: `timestamp` |
| `DELETE` | `/api/debts/:id` | Delete debt + all its payments (cascade, in one transaction) |

### Payments (Bearer token required)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/payments` | All payments across all user's debts |
| `GET` | `/api/debts/:debtId/payments` | Payments for a specific debt (ordered by date desc) |
| `POST` | `/api/debts/:debtId/payments` | Record payment. Body: `amount`, `dateMillis?`. Atomic: check→insert→deduct |
| `DELETE` | `/api/debts/:debtId/payments/:paymentId` | Delete payment + restore `currentAmount`. Returns `{id, amount, debtId, currentAmount}` |

---

## Auth Flow

```
1. POST /register → { accessToken, refreshToken, tokenType: "bearer" }
   (or POST /login)

2. All protected routes: Authorization: Bearer <accessToken>
   → get_current_user dependency decodes JWT, fetches User from DB
   → All CRUD queries filter by userId — user isolation enforced

3. When accessToken expires (30 min):
   POST /refresh { refreshToken } → new accessToken + new refreshToken
   (old refreshToken is deleted — token rotation)

4. POST /logout { refreshToken } + Bearer header → deletes refreshToken from DB

VK ID (POST /api/auth/vk, body: code, redirectUri, codeVerifier, deviceId, state?):
  a. Android client runs the VK ID SDK authorize flow (PKCE). The SDK generates
     and validates `state` — the backend never initiates the authorize request and
     only passes `state` through to the token exchange as a passthrough. Verifying
     that the returned `state` matches what was sent is the CLIENT's responsibility
     (login-CSRF protection).
  b. Backend exchanges code → access_token + user_id, fetches profile via
     /oauth2/user_info (unmasked email/fullName only if the client requested the
     `email` scope at authorize; otherwise those fields stay empty).
  c. Unknown vkId → auto-provision User (username vk_<vkId>, passwordHash NULL),
     store email/fullName. Known vkId → refresh email/fullName (only overrides
     with non-empty values).
  d. Concurrent first sign-in for the same vkId → unique index on vkId wins;
     the losing request catches IntegrityError, re-queries, and proceeds.
  e. Transient upstream failures (timeout/5xx) → 502; auth/logic failures → 401.
```

---

## Business Logic (critical)

### Record payment (crud/payments.py:8)
Atomic in one `db.commit()`:
1. Check debt exists and belongs to current user → 404
2. Check `currentAmount > 0` → 400 `"Долг уже полностью погашен"`
3. Insert Payment row
4. `currentAmount = max(0, currentAmount - amount)`

### Delete payment (crud/payments.py:38)
Atomic in one `db.commit()`:
1. Find payment + debt → 404 if missing
2. Delete payment row
3. `currentAmount += payment.amount` (restore)

### Full debt update (crud/debts.py:50)
- `paid = oldInitialAmount - oldCurrentAmount` (0 if oldInitialAmount == 0)
- `newCurrentAmount = max(0, newInitialAmount - paid)`
- Note: debt type (`I_OWE`/`OWE_ME`) is NOT editable

### Delete debt (crud/debts.py:102)
- `db.delete(debt)` triggers cascade deletion of all associated payments
- Defined in model: `payments = relationship(..., cascade="all, delete-orphan")`

### Active debts filter
- `GET /api/debts?active=true` → `WHERE currentAmount != 0`
- Logic in `crud/debts.py:7-11`

---

## Database Schema

4 tables, all columns camelCase:

```
users
├── id           INTEGER PK AUTOINCREMENT
├── username     TEXT UNIQUE NOT NULL
├── passwordHash TEXT          (bcrypt, NULL for VK users)
├── vkId         TEXT UNIQUE   (VK ID link, NULL for password users)
├── email        TEXT          (from VK profile)
├── fullName     TEXT          (from VK profile)
└── createdAt    BIGINT NOT NULL    (unix millis)

refresh_tokens
├── id        INTEGER PK AUTOINCREMENT
├── token     TEXT UNIQUE NOT NULL  (SHA-256 hash of secrets.token_urlsafe(64) — raw never stored)
├── userId    INTEGER FK → users.id
├── expiresAt BIGINT NOT NULL      (unix millis)
└── createdAt BIGINT NOT NULL

debts
├── id                   INTEGER PK AUTOINCREMENT
├── name                 TEXT NOT NULL
├── type                 TEXT NOT NULL    ("I_OWE" | "OWE_ME")
├── initialAmount        BIGINT NOT NULL
├── currentAmount        BIGINT NOT NULL
├── createdAt            BIGINT NOT NULL
├── reminderIntervalDays INTEGER          (NULL → reminders disabled)
├── lastReminderTimestamp BIGINT          (NULL → never reminded)
└── userId               INTEGER FK → users.id

payments
├── id         INTEGER PK AUTOINCREMENT
├── amount     BIGINT NOT NULL
├── dateMillis BIGINT NOT NULL
├── debtId     INTEGER FK → debts.id
```

---

## Testing

### Automated (pytest — 75 tests)

```bash
# Install dev deps inside container (first time)
docker compose exec api pip install -r requirements-dev.txt

# Run test suite
docker compose exec api python -m pytest tests/ -v
```

Tests use a temp-file SQLite database — no effect on production data.
Coverage: auth (register, login, refresh rotation, logout, expired tokens, refresh
token hashing, malformed token payload, rate-limit key resolution),
debts (CRUD, active filter, update recalc, cascade delete, user isolation, reminders),
payments (record, overpayment clamp, fully-paid error, delete restore, sorting),
VK ID (sign-in, profile sync, transient/error mapping, migration upgrade/downgrade).

### Manual/api — Bruno collection (`bruno/`)

49 requests with assertion scripts, run against the live dev backend
(`baseUrl` from the `dev` environment in `bruno/environments/dev.bru`). Run in
folder order (numbered): `00-setup` → `01-health` → `02-auth` → `03-debts` →
`04-payments` → `05-hardening`.

```bash
# Reset dev DB for a clean run (drops all dev data)
docker compose down && rm -f data/debts.db && docker compose up -d

# Install Bruno CLI once (v4+)
npm install -g @usebruno/cli

# Run the whole collection
cd bruno && bru run --env dev
```

- Post-response scripts assert status codes and business values; a thrown error marks the request failed.
- The CLI persists live tokens/ids into `environments/dev.bru` — revert it before committing:
  `git checkout bruno/environments/dev.bru`.
- See `bruno/README.md` for flow notes and the body-too-large curl check (413).

### Manual (curl)

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"user","password":"pass123"}'

# Login (save accessToken)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"user","password":"pass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

# Create debt
curl -X POST http://localhost:8000/api/debts \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Coffee","debtType":"I_OWE","initialAmount":500}'

# Record payment
curl -X POST http://localhost:8000/api/debts/1/payments \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"amount":100}'

# List active debts
curl "http://localhost:8000/api/debts?active=true" \
  -H "Authorization: Bearer $TOKEN"
```

Or use Swagger UI: `http://localhost:8000/docs`

---

## Adding New Migrations

1. Edit `app/models.py` (add/modify SQLAlchemy model)
2. Generate migration:
   ```bash
   docker compose exec api alembic revision --autogenerate -m "description"
   ```
3. Review the generated file in `alembic/versions/`
4. Restart container — migration auto-applies on startup

---

## Rate Limiting

- `POST /api/auth/login` — 5 requests/minute per IP
- `POST /api/auth/register` — 5 requests/minute per IP
- `POST /api/auth/refresh` — 5 requests/minute per IP
- `POST /api/auth/logout` — 10 requests/minute per IP
- `POST /api/auth/vk` — 5 requests/minute per IP
- Key: client IP from `X-Forwarded-For` (set by reverse proxy) with fallback to socket IP. The proxy MUST overwrite `X-Forwarded-For` with the real client IP (never append client-supplied values) — otherwise spoofing/rate-limit bypass.
- Configurable: edit `@limiter.limit(...)` decorators in `app/routers/auth.py`

---

## Deployment (production)

Production uses the `proxy` compose profile: an nginx container terminates TLS on `8443`
and proxies to the API over the internal network. The API publishes `127.0.0.1:8000` only.

```bash
# 1. Prepare env (`.env` in project root)
ENVIRONMENT=production
JWT_SECRET=$(openssl rand -hex 32)   # >= 32 chars, fail-fast enforced
API_PATH_PREFIX=$(openssl rand -base64 32 | tr '/+' '_-')   # embed in mobile app
# CORS_ORIGINS=...  # optional

# 2. Certificates on the host (owned by the renewal tool)
#    /root/cert/ip/fullchain.pem
#    /root/cert/ip/privkey.pem
#    The cert must have SAN = IP (CN is ignored by Android), chain trusted by Android.

# 3. Make /data writable for the non-root container user
mkdir -p data && sudo chown 1001:1001 data

# 4. Start
docker compose --profile proxy up -d --build

# 5. Hook cert renewal → nginx reload (run from project root)
certbot renew --deploy-hook "$(pwd)/reload-nginx.sh"
```

Verify: `openssl x509 -in /root/cert/ip/fullchain.pem -noout -text | grep -i "IP Address"`
Then `curl -k https://<server-ip>:8443/health` → `{"status":"ok"}`.

- The proxy MUST overwrite `X-Forwarded-For` with the real client IP — nginx is configured
  to set `X-Forwarded-For $remote_addr` (never appends client-supplied values).
- nginx access logs are disabled — the unguessable path prefix never appears in logs.
- If your CA is not publicly trusted by Android, skip straight to a Wifi/HTTPS debug build
  or add the CA to the app's trust store.

---

## Dependencies

```
fastapi           # Web framework
uvicorn[standard]  # ASGI server
sqlalchemy        # ORM
alembic           # Migrations
pydantic          # Validation
passlib[bcrypt]   # Password hashing
bcrypt==4.3.0     # Pinned for passlib 1.7.4 compat
python-jose[cryptography]  # JWT
slowapi           # Rate limiting
httpx             # VK ID OAuth client
```

All versions pinned in `requirements.txt` — update deliberately, run `pip-audit -r requirements.txt` before release.

---

## CI/CD

GitHub Actions workflow triggers on `git tag v*` (not on push to main):

```
git tag v0.1.0 → Lint (ruff) → Test (pytest, 75 tests) → Security (pip-audit) → Build & Push to ghcr.io
```

Docker images published at `ghcr.io/evgeny1101/debttrackerapi` with tags:
- `:latest` — latest release
- `:0.1.0` — specific version
- `:0.1` — minor version

### Release checklist

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit and push to main
git add -A && git commit -m "Release v0.1.0"
git push origin main

# 4. Tag and push — CI triggers automatically
git tag v0.1.0 && git push origin v0.1.0

# 5. (optional) Create GitHub Release
gh release create v0.1.0 --title "v0.1.0" --notes-file CHANGELOG.md
```
