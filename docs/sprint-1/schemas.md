# Schemas Sprint 1

Документ описывает Pydantic-модели, которые используются как source of truth для web-роутеров. Все схемы лежат в `src/sda/web/schemas/` и рассчитаны на `pydantic v2`.

## Общие enum и ограничения

### Result format

- `csv_base64` - один CSV-файл, закодированный в `content_base64`.
- `zip_base64` - ZIP-архив для multi-file generate-сценария.

### Anonymization methods

- `keep`
- `mask`
- `remove`
- `pseudonymize`
- `generalize_year`
- `generalize_date`

### Лимиты

- Generate `row_count`: `1..10000`
- Upload/Similar входной CSV: до `10000` строк
- Колонки в upload/analyze: до `128`
- Preview rows: до `5` в ответе, до `20` в запросе analyze
- Имена файлов результата: без path separators, обязательный суффикс `.csv`

## `src/sda/web/schemas/generate.py`

### `GenerateTemplateSummary`

- `template_id: GenerateTemplateId`
- `name: str`
- `description: str`
- `columns: list[str]`
- `default_rows: int`
- `max_rows: int`

Использование:

- элемент списка для `GET /generate/templates`

Валидации:

- `columns` не пустой, уникальный список
- в именах колонок нет control characters

### `GenerateTemplateDetail`

Наследует `GenerateTemplateSummary`, добавляет:

- `recommended_rows: list[int]`
- `relations: list[str]`
- `columns_detail: list[GenerateTemplateColumn]`

Использование:

- ответ `GET /generate/templates/{template_id}`

### `GenerateRunRequest`

- `items: list[GenerateRunItem]`
- `result_format: ResultFormat = zip_base64`
- `random_seed: int | None`

Валидации:

- хотя бы один item
- один и тот же `template_id` нельзя запрашивать дважды
- `result_format=csv_base64` разрешен только для одного item

### `GenerateRunResponse`

- `result_format: ResultFormat`
- `file_name: str`
- `generated_files: list[GeneratedFile]`
- `archive_base64: str | None`
- `total_rows: int`
- `warnings: list[str]`

Использование:

- ответ `POST /generate/run`

## `src/sda/web/schemas/anonymize.py`

### `UploadedCsvColumn`

- `index: int`
- `name: str`
- `inferred_type: str`
- `sample_values: list[str]`
- `null_ratio: float`
- `unique_ratio: float`
- `suggested_method: AnonymizationMethod | None`
- `suggestion_confidence: float | None`
- `pii_hint: str | None`

Использование:

- описание одной колонки после `POST /anonymize/upload`

### `AnonymizationRule`

- `column_name: str`
- `method: AnonymizationMethod`
- `params: dict[str, Any]`

Использование:

- элемент массива `rules` в `AnonymizeRunRequest`

Валидации:

- `column_name` trimmed и не пустой
- допускаются arbitrary params под конкретный метод, но на уровне use-case должен быть дополнительный semantic validation

### `AnonymizeUploadResponse`

- `upload_id: str`
- `file_name: str`
- `row_count: int`
- `column_count: int`
- `columns: list[UploadedCsvColumn]`
- `preview_rows: list[dict[str, str | None]]`
- `delimiter: str`
- `encoding: str`
- `suggestions_included: bool`
- `warnings: list[str]`

Использование:

- ответ `POST /anonymize/upload`

### `AnonymizeRunRequest`

- `upload_id: str`
- `rules: list[AnonymizationRule]`
- `output_format: OutputFormat = csv_base64`
- `file_name: str | None`

Валидации:

- `rules` должны ссылаться на уникальные колонки
- `file_name` не должен содержать путь и должен заканчиваться на `.csv`

### `AnonymizeRunResponse`

- `upload_id: str`
- `file_name: str`
- `row_count: int`
- `column_count: int`
- `output_format: OutputFormat`
- `content_base64: str`
- `applied_rules: list[AnonymizationRule]`
- `warnings: list[str]`

Использование:

- ответ `POST /anonymize/run`

## `src/sda/web/schemas/similar.py`

### `SimilarAnalyzeRequest`

- `preview_rows_limit: int = 5`
- `has_header: bool = true`
- `delimiter: str = ","`

Использование:

- формальная схема для non-file части `multipart/form-data` запроса `POST /similar/analyze`

### `SimilarAnalyzeResponse`

- `analysis_id: str`
- `file_name: str`
- `row_count: int`
- `column_count: int`
- `columns: list[SimilarColumnProfile]`
- `preview_rows: list[dict[str, str | None]]`
- `summary: list[str]`
- `warnings: list[str]`

Использование:

- ответ `POST /similar/analyze`

### `SimilarRunRequest`

- `analysis_id: str`
- `target_rows: int`
- `output_format: SimilarOutputFormat = csv_base64`
- `random_seed: int | None`
- `file_name: str | None`

Валидации:

- `target_rows` в диапазоне `1..10000`
- `file_name` валидируется так же, как в generate/anonymize

### `SimilarRunResponse`

- `analysis_id: str`
- `file_name: str`
- `row_count: int`
- `column_count: int`
- `output_format: SimilarOutputFormat`
- `content_base64: str`
- `warnings: list[str]`

Использование:

- ответ `POST /similar/run`

## Общая ошибка

### `ErrorResponse`

- `error_code: str`
- `message: str`
- `details: dict[str, Any] | None`
- `request_id: str | None`

Использование:

- единая структура 4xx/5xx ответов для всех endpoint’ов

## Что важно для роутеров

- Generate/Anonymize/Similar схемы можно импортировать напрямую в FastAPI handlers.
- Для upload endpoints сам файл будет приниматься через `UploadFile`, а остальные поля формы могут маппиться в schema вручную.
- Semantic checks, зависящие от содержимого CSV или наличия `upload_id`/`analysis_id`, остаются на уровне use-case, не Pydantic.
