---
name: debttracker-lint
description: Run ruff linter and formatter on all Python files, auto-fix when possible
---

## What I do

- Run `ruff check .` to find issues
- Run `ruff check --fix .` to auto-fix safe issues
- Run `ruff format --check .` to verify formatting
- Run `ruff format .` to auto-format
- Report: all clear or remaining issues

## Execution order

1. `ruff check .` — if errors found, try `ruff check --fix .`
2. `ruff check .` again — report remaining errors
3. `ruff format --check .` — if not formatted, run `ruff format .`
4. Report: all clear or remaining issues

## Commands reference

```bash
# Lint check
docker compose exec api python -m ruff check .

# Auto-fix lint issues
docker compose exec api python -m ruff check --fix .

# Check formatting
docker compose exec api python -m ruff format --check .

# Auto-format
docker compose exec api python -m ruff format .
```

> Use `python -m ruff` inside the container — dev deps install to user-site (`~/.local/bin`), not on `PATH` for non-login `docker compose exec`.

## Rules suppression (configured in pyproject.toml)

- `N815` — camelCase in models.py/schemas.py (matching Android Room entities)
- `B008` — `Depends()` in router defaults (FastAPI standard pattern)
- `E402` — imports after env var setup in conftest.py (required for test config)
