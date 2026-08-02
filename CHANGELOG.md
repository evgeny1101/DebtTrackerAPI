# Changelog

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
- OpenCode skills: `debttracker-check`, `debttracker-lint`
- AGENTS.md with full project documentation
- Swagger UI auto-generated docs
