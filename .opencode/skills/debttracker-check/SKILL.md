---
name: debttracker-check
description: Build, start, and test the DebtTracker API — run test suite and smoke-check endpoints
---

## What I do

- Start the Docker container (build if needed)
- Install test dependencies inside the container
- Run the pytest suite (45 tests)
- Quick smoke test: health check, register, login, create debt, record payment
- Report results

## Execution order

1. Build + start container
2. Install test deps (`pip install -r requirements-dev.txt`) inside container
3. Run pytest — if any test fails, report the failure and check `docker compose logs`
4. If all tests pass, run smoke test
5. Report: pass/fail counts + API smoke status

## Commands reference

### Start the service

```bash
docker compose up -d --build
```

Wait for the container to be ready (check logs for "Uvicorn running").

### Install test dependencies (skip if already installed)

```bash
docker compose exec api pip install -q -r requirements-dev.txt
```

### Run test suite

```bash
docker compose exec api python -m pytest tests/ -v
```

Expected: 45 passed, 0 failed.

### Smoke test — health check

```bash
curl -s http://localhost:8000/health
```

Expected: `{"status":"ok"}`

### Smoke test — register, create debt, record payment

```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"smoketest","password":"smoke123"}'

LOGIN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"smoketest","password":"smoke123"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

curl -s -X POST http://localhost:8000/api/debts \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Smoke","debtType":"I_OWE","initialAmount":100}'

curl -s -X POST http://localhost:8000/api/debts/1/payments \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"amount":50}'

curl -s "http://localhost:8000/api/debts?active=true" \
  -H "Authorization: Bearer $TOKEN"
```

Expected: all responses 200/201, full flow works end-to-end.
