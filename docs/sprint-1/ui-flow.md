# UI Flow Sprint 1 (MVP)

## 1. Generate Flow
1. User opens Generate page.
2. User selects one or more templates.
3. User enters row count.
4. User clicks `Generate`.
5. Frontend calls `POST /generate`.
6. On `200`, frontend starts CSV download.
7. On error, frontend shows readable message from `detail`.

## 2. Anonymize Flow
1. User opens Anonymize page.
2. User uploads CSV file.
3. Frontend optionally calls `POST /suggest` for rule hints.
4. UI displays columns and default action `keep` for each.
5. User edits methods per column (`keep/mask/redact/pseudo`).
6. User clicks `Anonymize`.
7. Frontend sends `POST /anonymize` (`file` + `rules`).
8. On `200`, frontend starts download of anonymized CSV.
9. On error, frontend highlights problem and shows `detail`.

## 3. Download UX Rules
1. Download action must be explicit and retryable.
2. Filename should come from `Content-Disposition`.
3. If browser blocks auto-download, user sees fallback link/button.

## 4. Error UX Rules
1. Empty CSV -> show "uploaded file is empty" equivalent.
2. Bad delimiter/malformed CSV -> show parse error hint.
3. Wrong method/validation error -> show invalid field/method.
4. Network/server issue -> show generic retry message and keep form state.
