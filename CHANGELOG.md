# Changelog

## [0.5.1] — 2026-10-23

### CI
- **Pinned ruff version in the release workflow** — `ruff-action@v3` could not find a ruff pin in `pyproject.toml` and silently installed the latest ruff (0.17.2), whose stricter isort ordering failed lint on code that 0.16.3 (the dev pin in `requirements-dev.txt`) accepted. The workflow now reads the version from `requirements-dev.txt`; import order in `app/routers/auth.py` normalized so both versions pass
- v0.5.0 tag/release withdrawn immediately after the lint failure — no image was pushed, nobody consumed it; account deletion ships in this release

## [0.5.0] — 2026-10-23

> Superseded by 0.5.1 (CI lint failure, tag withdrawn before publication)

### Account deletion
- **`DELETE /api/auth/me`** — user deletes their own account in a single transaction: debts, payments, and refresh tokens cascade via ORM relationships (`db.delete(user)` + commit). RuStore compliance: self-service account removal
- Works identically for password and VK ID accounts (VK profile itself is untouched — no calls to VK)
- Old access token stops working immediately (`get_current_user` → 401 "User not found"), refresh and login fail with 401, `username` becomes free for re-registration
- New `app/crud/users.py` (`delete_user`); INFO log contains only the numeric user id — no username/email/vkId
- Rate-limited 5/min per IP like login/register; no schema changes or migrations
- Test suite grown to 84 tests (6 new): cascade wipe, credential invalidation, isolation, username reuse, VK account deletion
- Bruno collection: `06-account/` folder appended (runs last — deletion invalidates the session used by earlier folders)

## [0.4.3] — 2026-09-20

### Cleanup
- **Dropped `passlib`** — password hashing now uses the native `bcrypt` library directly (`hashpw`/`checkpw` in `app/auth.py`). Same `$2b$` hash format, existing password hashes verify without migration; malformed hashes in DB now return `False` instead of raising. Removes the noisy startup warning `error reading bcrypt version` (passlib 1.7.4 is unmaintained and incompatible with bcrypt ≥ 4.1 version introspection)
- **Silenced `SAWarning` on refresh-token deletes** — `confirm_deleted_rows=False` on the `RefreshToken` mapper (concurrent refresh/logout legitimately deletes an already-removed row)
- No API or schema changes; docs updated (78 tests)

## [0.4.2] — 2026-09-20

### Fixes / diagnostics (VK ID sign-in)
- **VK error details surfaced in logs**: `error`/`error_description` from VK responses are now extracted regardless of HTTP status (VK ID returns some errors with HTTP 200). The endpoint still answers 401, but the WARNING log now names the exact VK error and description
- **Missing-token / missing-user responses log VK response field names** (names only, never values) — previously the response body was silently discarded, masking the root cause
- No client-visible behavior change (same 401/502 mapping); +3 tests → 78 total

## [0.4.1] — 2026-09-13

### Fixes / hardening (VK ID sign-in)
- **`state` stays optional** and is passed through as-is; validating the returned `state` is the Android client/SDK's responsibility (login-CSRF protection). Unmasked `email`/`fullName` only arrive if the client requested the `email` scope at authorize
- **Malformed VK responses** (non-JSON body, missing `access_token`/`user_id`/`user`, wrong field types) now map to 401 instead of crashing with 500
- **Transient upstream failures** (network errors, timeouts, HTTP 5xx from VK) map to 502 instead of 401
- **Concurrent first sign-in** for the same `vkId` handles the unique-index `IntegrityError` — the loser rolls back, re-queries, and continues
- **Existing VK users get profile refresh** on every sign-in; empty values never overwrite stored `email`/`fullName`
- **Migration `003` downgrade** is now safe: refuses to run if VK users with `passwordHash = NULL` exist, restores the `NOT NULL` constraint, and runs inside `batch_alter_table`
- **`httpx` added to `pyproject.toml`** production dependencies (was only in `requirements.txt`)
- Test suite grown to 75 tests (15 new tests): VK response validation, transient error mapping, profile refresh, username collision, migration upgrade/downgrade

## [0.4.0] — 2026-09-10

### VK ID sign-in
- **`POST /api/auth/vk`** — authenticate/sign-up via VK ID and receive the same access + refresh JWTs as the password flow
- Public-app OAuth: PKCE (`codeVerifier`), `code`/`redirectUri`/`deviceId`/`state` passed through to `https://id.vk.ru/oauth2/auth`, profile fetched via `/oauth2/user_info`
- **Auto-provisioning**: unknown VK accounts create a user with synthetic `username = vk_<vkId>`, `passwordHash = NULL`, storing `email`/`fullName` from the VK profile
- New nullable `users` columns: `vkId` (unique), `email`, `fullName`; `passwordHash` now nullable. Migration `003`
- `username` prefix `vk_` reserved at registration (409 "Username not allowed"); suffix fallback (B) guards against legacy collisions
- Password login rejects VK-only users (no password hash)
- New `app/vk.py` client (`httpx`), `VK_CLIENT_ID` env (empty → endpoint returns 503), rate-limited 5/min
- Test suite grown to 60 tests (7 new VK tests), docs and `.env.example`/`docker-compose.yml` updated

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
