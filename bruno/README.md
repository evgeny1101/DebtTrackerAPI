# DebtTracker API — Bruno collection

Manual test collection for the dev backend (localhost:8000, no API path prefix).

## Setup

1. Bruno → Open Collection → select this `bruno/` folder.
2. The **dev** environment is already provided in `environments/dev.bru`
   (`baseUrl = http://localhost:8000`, token/id vars start empty).
3. Activate the **dev** environment.
4. Run requests in order (folders are numbered): `00-setup` → `01-health` → `02-auth` → `03-debts` → `04-payments` → `05-hardening`.

Tokens and ids are captured automatically by post-response scripts (do not fill them by hand).

> **Note:** running the collection via CLI (`bru run --env dev`) writes the live
> tokens/ids back into `environments/dev.bru`. Revert it before committing:
> `git checkout bruno/environments/dev.bru`.

## Flow notes

- **Setup** registers `alice` and `bob`. On re-runs a register may return `409` — use `02-auth/04_login.bru` to refresh tokens instead.
- **Rate limiting**: login/register/refresh are limited to 5/min per IP. All auth requests send a fixed
  `X-Forwarded-For` header so the limit bucket is consistent. To see the limit work, run
  `02-auth/04_login.bru` (or a rate-limit request in `05-hardening`) six times quickly — the 6th returns `429`.
- **Ids are sequential** (SQLite autoincrement). If you reset the DB (`rm data/debts.db` + restart), ids restart at 1.
- Update-recalc (`04-payments/03`) must run after payments `01` and `02` on the same debt.
- `05-hardening/03_body-too-large` cannot be expressed in Bruno, use curl instead:
  ```bash
  # Create a >1MB JSON file and post it
  python3 -c "print('{\"name\":\"' + 'x'*1100000 + '\"}')" > /tmp/big.json
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/debts \
    -H 'Content-Type: application/json' -d @/tmp/big.json   # expect 413
  ```