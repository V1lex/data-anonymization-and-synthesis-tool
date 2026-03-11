# Test Plan Sprint 1 (MVP)

## 1. Purpose
Document the minimum test set and acceptance criteria for MVP so that Sprint 2 can build smoke/e2e tests without extra clarification.

## 2. In Scope (MVP)
1. Generate CSV from predefined templates.
2. Anonymize any uploaded CSV by per-column rules.
3. Download resulting CSV from Generate/Anonymize flows.
4. Basic error handling for invalid input.

## 3. Out of Scope (Sprint 1)
1. Load/performance testing.
2. Security pentest.
3. Similar/Synthesize quality validation (post-MVP).

## 4. Test Levels
1. Contract/API checks (HTTP status, payload schema, headers).
2. Functional checks (CSV structure, row count, applied rules).
3. Negative checks (invalid files/params/methods).
4. Smoke flow checks (happy paths end-to-end).

## 5. Entry/Exit Criteria
### Entry
1. Sprint-1 docs are approved (`scope`, `architecture`, `api-contracts`, `schemas`, `templates`).
2. Endpoints are available in local environment.

### Exit
1. All acceptance criteria from section 6 are green.
2. No blocker/critical defects in MVP flows.
3. Smoke test checklist from section 8 is executable without verbal handover.

## 6. Acceptance Criteria

### 6.1 Generate CSV
1. Given a valid generate request with known template and `rows > 0`, API returns `200`.
2. Response has `Content-Type: text/csv`.
3. Response has download header (`Content-Disposition` with filename ending in `.csv`).
4. CSV has header row matching template schema exactly.
5. CSV has exactly requested number of data rows.
6. CSV is parseable by standard CSV reader with configured delimiter.
7. For unknown template, API returns client error (`400`/`422`) with readable message.
8. For `rows <= 0`, API returns client error (`400`/`422`).

### 6.2 Anonymize Any CSV
1. Given a valid CSV upload and valid per-column rules, API returns `200`.
2. Output CSV keeps same column order as input.
3. Output CSV keeps same number of rows as input.
4. Rule `keep` leaves values unchanged.
5. Rule `mask` changes value format to masked representation (non-empty, deterministic policy).
6. Rule `redact` removes/hides value according to contract.
7. Rule `pseudo` replaces values consistently: same input value in same column -> same output value.
8. If rule references unknown column, API returns client error (`400`/`422`) with column name.
9. If rule method is unsupported, API returns client error (`400`/`422`) with allowed methods.

### 6.3 Result Download Scenario
1. User can trigger download after successful Generate response.
2. User can trigger download after successful Anonymize response.
3. Downloaded file opens as valid CSV in spreadsheet/editor.
4. Filename in `Content-Disposition` is not empty and extension is `.csv`.
5. Large enough sample file (at least 100 rows) downloads without truncation.

## 7. Negative Test Cases (Required)

### CSV/Input Negatives
1. Empty file body -> client error (`400`/`422`), explicit message "empty CSV" equivalent.
2. CSV with header only and no data rows -> defined behavior (either valid empty dataset or explicit validation error) must be stable and documented.
3. Malformed CSV with broken quotes/newlines -> client error (`400`/`422`).
4. Wrong delimiter (for example semicolon file treated as comma) -> deterministic behavior:
If auto-detect is enabled: parsing succeeds with detected delimiter.
If auto-detect is disabled: parsing fails with readable delimiter error.
5. Non-CSV file with `.csv` name -> client error (`400`/`422`) if parsing fails.

### API Negatives
1. Wrong HTTP method on endpoint -> `405 Method Not Allowed`.
2. Missing required request fields -> `422 Unprocessable Entity`.
3. Invalid JSON type for fields (`rows` as string, `rules` as array when object expected) -> `422`.
4. Oversized request (if limit configured) -> `413` or documented equivalent.

### Domain Negatives
1. Unknown template name in Generate -> `400`/`422`.
2. Invalid anonymization method (`md5`, `encrypt`, etc.) -> `400`/`422`.
3. Rules payload includes duplicate/conflicting config for one column -> deterministic validation error.

## 8. Smoke Checklist (for Sprint 2)
1. `GET /health` returns `200`.
2. Generate flow: request template + rows -> download CSV -> validate header and row count.
3. Anonymize flow: upload CSV + rules -> download CSV -> validate row count and transformed values.
4. Negative smoke: send wrong HTTP method and verify `405`.
5. Negative smoke: upload empty CSV and verify expected client error.

## 9. E2E Scenarios (Baseline)
1. Generate users CSV (50 rows), open file, verify schema and count.
2. Upload generated users CSV to Anonymize, apply mixed rules (`keep/mask/redact/pseudo`), download and validate transformations.
3. Upload malformed CSV and verify non-200 response with actionable error text.

## 10. Definition of Done (T009)
1. Document contains acceptance criteria for Generate, Anonymize, and download scenario.
2. Required negative cases are listed (empty CSV, bad delimiter, wrong method, invalid rule/template).
3. Document is sufficient as direct input to smoke/e2e test implementation in Sprint 2.
