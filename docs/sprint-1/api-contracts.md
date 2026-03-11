# API Contracts Sprint 1 (MVP)

## 1. Conventions
1. Base URL: `/api/v1` (or project default prefix if configured differently).
2. Success response for file-producing endpoints: `200` + `text/csv`.
3. Validation errors: `422` (framework validation) or `400` (domain validation).
4. Method mismatch: `405`.

## 2. Endpoints

### 2.1 Health
`GET /health`

Response `200`:
```json
{
  "status": "ok"
}
```

### 2.2 Generate CSV
`POST /generate`

Request body:
```json
{
  "template": "users",
  "rows": 100,
  "delimiter": ",",
  "seed": 42
}
```

Response `200`:
Headers:
1. `Content-Type: text/csv`
2. `Content-Disposition: attachment; filename="<template>.csv"`

Body: CSV bytes.

Validation errors:
1. Unknown template -> `400`/`422`.
2. Invalid `rows` (`<=0`) -> `400`/`422`.

### 2.3 Anonymize CSV
`POST /anonymize`

Request:
1. `multipart/form-data`
2. Field `file`: uploaded CSV
3. Field `rules`: JSON object (column -> method config)

Example `rules`:
```json
{
  "email": { "method": "mask" },
  "phone": { "method": "redact" },
  "full_name": { "method": "pseudo" },
  "city": { "method": "keep" }
}
```

Response `200`:
Headers:
1. `Content-Type: text/csv`
2. `Content-Disposition: attachment; filename="anonymized.csv"`

Body: anonymized CSV bytes.

Validation errors:
1. Empty/malformed CSV -> `400`/`422`.
2. Unknown column in rules -> `400`/`422`.
3. Unsupported method -> `400`/`422`.

### 2.4 Suggest PII (supporting endpoint)
`POST /suggest`

Request:
1. `multipart/form-data`
2. Field `file`: uploaded CSV

Response `200`:
```json
{
  "columns": [
    {
      "name": "email",
      "suggested_method": "mask",
      "confidence": 0.92,
      "reason": "column name pattern + value pattern"
    }
  ]
}
```

Notes:
1. Suggestions are advisory; user still chooses final anonymization rules.
2. Default fallback for unspecified columns in Anonymize is `keep`.

### 2.5 Similar/Synthesize (post-MVP)
`POST /similar`

Status in Sprint 1 docs: contract draft only, implementation planned post-MVP.

## 3. Error Response Format (recommended baseline)
```json
{
  "detail": "human-readable error message"
}
```

If domain-specific structured errors are used, they must still include readable `detail`.

## 4. File Download Contract
Applies to `POST /generate` and `POST /anonymize`:
1. Response must be directly downloadable as `.csv`.
2. Filename is always provided in `Content-Disposition`.
3. CSV encoding is UTF-8 unless explicitly configured otherwise.
