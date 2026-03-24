# T026 - MVP Smoke/E2E Test Report

Date: 2026-03-24
Role: QA (Andrey)
Branch: `task/T025-docker-compose-mvp`

## Scope

Checked end-to-end MVP scenario before Demo 2:
- Generate flow from request to downloadable CSV
- Anonymize flow from CSV upload to downloadable anonymized CSV
- README alignment with actual run mode and current API/UI behavior

## Test Environment

- OS: Windows (local dev environment)
- Python: system Python 3.13
- Backend start command:

```bash
uvicorn --app-dir src sda.web.app:app --host 127.0.0.1 --port 8000
```

## Executed Smoke/E2E Steps

### A. Generate flow (E2E)

1. `GET /api/v1/generate/templates` -> `200 OK`
2. `POST /api/v1/generate/run` with payload:

```json
{
  "items": [{"template_id": "users", "row_count": 5}],
  "locale": "ru_RU"
}
```

3. Response `200 OK`, `result_format = "csv_base64"`
4. Decoded CSV saved to `artifacts/e2e/users_generated.csv`

Result: PASS

### B. Anonymize flow (E2E)

1. `POST /api/v1/anonymize/upload` with `users_generated.csv` -> `200 OK`
2. `POST /api/v1/anonymize/run` with rules:
- `full_name -> pseudonymize`
- `email -> mask`
- `phone -> redact`
3. Response `200 OK`, `result_format = "csv_base64"`
4. Decoded CSV saved to `artifacts/e2e/users_anonymized.csv`
5. Verified changed values in first row for `full_name`, `email`, `phone`

Result: PASS

## Artifacts

- `artifacts/e2e/smoke_e2e_summary.json`
- `artifacts/e2e/uvicorn.log`
- `artifacts/e2e/users_generated.csv`
- `artifacts/e2e/users_anonymized.csv`

## Findings

Blocking bugs: none found in tested flows.

Notes:
- Verification was executed through API end-to-end (upload/process/download).
- Frontend container mode remains documented in README as the primary one-command MVP run.

## Readiness for Demo 2

Status: READY

MVP works from startup to downloadable result for both key flows (`generate`, `anonymize`) in smoke/e2e scope.