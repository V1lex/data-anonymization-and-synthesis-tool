# SDA (Synthetic Data Anonymizer)

MVP supports two end-to-end flows:
- `Generate`: create synthetic CSV files.
- `Anonymize`: upload CSV, apply anonymization rules, download anonymized CSV.

## Actual Run Modes

### 1) Docker Compose (frontend + backend)

```bash
docker compose up --build
```

Available endpoints after startup:
- Frontend UI: `http://localhost:8080`
- Backend API: `http://localhost:8000/api/v1`
- Backend healthcheck: `http://localhost:8000/api/v1/health`
- OpenAPI docs: `http://localhost:8000/docs`

Stop:

```bash
docker compose down
```

### 2) Local backend run (QA smoke)

```bash
python -m pip install -r requirements.txt
uvicorn --app-dir src sda.web.app:app --host 127.0.0.1 --port 8000
```

## API Flows (Current Contract)

Generate flow:
1. `GET /api/v1/generate/templates`
2. `POST /api/v1/generate/run`
3. Decode `content_base64` (single template) or `archive_base64` (multiple templates)

Anonymize flow:
1. `POST /api/v1/anonymize/upload` (multipart form-data, CSV file)
2. `POST /api/v1/anonymize/run` (`upload_id` + rules)
3. Decode `content_base64` to anonymized CSV

## Smoke/E2E Status

Latest smoke/e2e report: [docs/sprint-2/test-report-mvp.md](docs/sprint-2/test-report-mvp.md)

Artifacts from the latest run:
- `artifacts/e2e/users_generated.csv`
- `artifacts/e2e/users_anonymized.csv`
- `artifacts/e2e/smoke_e2e_summary.json`