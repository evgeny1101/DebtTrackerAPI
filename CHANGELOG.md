# Changelog

## [0.3.0] — 2026-08-20

### Production deployment
- **nginx TLS termination** (`8443`) via new `proxy` compose profile — API is bound to `127.0.0.1:8000` only, nginx proxies over an internal network
- **Unguessable `API_PATH_PREFIX`** for all API routes — production refuses to start without a >= 32 char random prefix (fail-fast in `validate_production_config`)
- **`ENABLE_DOCS`** switch — `/docs`, `/redoc`, `/openapi.json` disabled in production by default
- **`reload-nginx.sh`** certificate renewal hook (`certbot renew --deploy-hook`/`acme.sh --reloadcmd`)
- nginx: HSTS header, `server_tokens off`, access logs disabled (the path prefix never appears in logs), `client_max_body_size 1m`
- Docker/compose now forwards target env vars (`ENVIRONMENT`, `JWT_SECRET`, `CORS_ORIGINS`, …) from `.env` with sensible defaults

### Hardening
- **Request body size limit** — 1 MB, oversized bodies rejected with `413 Payload too large` (matches nginx limit)

### Developer Experience
- **Bruno manual API test collection** (`bruno/`) — 49 requests with assertion scripts across auth/debts/payments/rate-limiting, plus a dedicated `dev` environment
- Production-config unit tests (JWT secret + prefix requirements, `api_path_prefix()` helper), tests for docs toggle and 413 body limit
- README + AGENTS.md updated with the production deployment checklist and Bruno usage

## [0.2.0] — 2026-08-20

### Security hardening
- **Fail-fast production config**: app refuses to start if `JWT_SECRET` is default or < 32 chars when `ENVIRONMENT=production` (was a startup warning only)
- **Refresh tokens stored as SHA-256 hashes** — raw token is never persisted (previously stored plaintext in DB). Migration `002` resets all existing sessions
- **Rate limiting keyed on `X-Forwarded-For`** — works correctly behind a reverse proxy, resists IP spoofing; added limits on `/refresh` (5/min) and `/logout` (10/min)
- **CORS locked down**: origins read from `CORS_ORIGINS` env (empty by default), `allow_credentials` disabled (was `*` + credentials)
- **Container runs as non-root** `appuser` (uid 1001)
- **Input hardening**: debt names capped at 200 chars, `reminderIntervalDays` must be > 0
- **Malformed JWT `sub`** now returns 401 instead of crashing with 500
- **Dependencies pinned** (exact versions in `requirements.txt`), dev deps split to `requirements-dev.txt`, `pip-audit` added to CI

### Developer Experience
- Test suite grown to 45 tests (refresh-token hashing, malformed token payload, rate-limit key resolution)

## [0.1.0] — 2026-08-02

### Auth
- JWT authentication with access + refresh tokens
- Token rotation on refresh (old token invalidated)
- User registration and login
- Refresh token invalidation on logout
- Expired refresh token cleanup on startup

### Debts
- CRUD: create, list (all / active / with-reminders), get, full update, patch, delete
- `?active=true` filter: returns only debts with `currentAmount != 0`
- Full update automatically recalculates `currentAmount` based on amount already paid
- Debt type (`I_OWE` / `OWE_ME`) is not editable
- Delete cascades to all associated payments
- PATCH `current-amount` and `last-reminder-timestamp`

### Payments
- Atomic recording: check debt exists → verify not fully paid → insert payment → deduct `currentAmount`
- Overpayment clamps `currentAmount` to 0
- Payment on fully paid debt returns 400 "Долг уже полностью погашен"
- Atomic deletion: find payment → delete → restore `currentAmount`
- List all payments across debts, list payments per debt (sorted by date desc)

### Security
- Multi-user data isolation (every query filters by `userId`)
- bcrypt password hashing
- Rate limiting on auth endpoints (5 req/min per IP)
- `JWT_SECRET` default value warning on startup

### Infrastructure
- Docker + docker-compose with SQLite volume mount
- Alembic migrations (auto-applied on startup via entrypoint.sh)
- `.dockerignore` — clean build context

### Developer Experience
- 41 automated tests (pytest in Docker, temp-file SQLite DB)
- Structured logging with `LOG_LEVEL` env variable
- Ruff linter + formatter with project rules (0 errors)
- GitHub Actions CI/CD: lint → test → build & push to ghcr.io on tag
- OpenCode skills: `debttracker-check`, `debttracker-lint`
- AGENTS.md with full project documentation
- Swagger UI auto-generated docs
