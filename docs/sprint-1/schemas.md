# Схемы Sprint 1

Документ описывает Pydantic-модели, которые используются как источник истины для web-роутеров. Все схемы лежат в `src/sda/web/schemas/` и рассчитаны на `pydantic v2`.

## Общие enum и ограничения

### Формат результата

- `csv_base64` - один CSV-файл, закодированный в `content_base64`.
- `zip_base64` - ZIP-архив для сценария генерации нескольких файлов.

### Методы анонимизации

- `keep`
- `mask`
- `redact`
- `pseudonymize`
- `generalize_year`

### Лимиты

- `row_count` в Generate: `1..10000`
- Входной CSV для upload/analyze: до `10000` строк
- Колонки в upload/analyze: до `128`
- Preview rows: до `5` в ответе, до `20` в запросе analyze

## `src/sda/web/schemas/generate.py`

### `GenerateTemplateSummary`

- `template_id: GenerateTemplateId`
- `name: str`
- `description: str | None`
- `preview_columns: list[str] | None`

Использование:

- элемент списка для `GET /generate/templates`

Валидации:

- если `preview_columns` передан, он содержит короткий список колонок для превью, а не полный список
- если `preview_columns` передан, он не должен быть пустым и не должен содержать дубликатов
- в именах колонок нет control characters

### `GenerateTemplateDetail`

Наследует `GenerateTemplateSummary`, добавляет:

- `columns: list[GenerateTemplateColumn]`

Использование:

- ответ `GET /generate/templates/{template_id}`

### `GenerateRunRequest`

- `items: list[GenerateRunItem]`

Валидации:

- хотя бы один элемент в `items`
- один и тот же `template_id` нельзя запрашивать дважды

### `GenerateRunResponse`

- `result_format: ResultFormat`
- `file_name: str`
- `generated_files: list[GeneratedFile]`
- `content_base64: str | None`
- `archive_base64: str | None`
- `total_rows: int`
- `warnings: list[str]`

Использование:

- ответ `POST /generate/run`

Поведение:

- если в запросе один шаблон, backend возвращает `result_format=csv_base64` и заполняет `content_base64`
- если в запросе несколько шаблонов, backend возвращает `result_format=zip_base64` и заполняет только `archive_base64`
- `generated_files` в режиме нескольких файлов содержит только метаданные файлов без дублирования `content_base64`

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

- `column_name` нормализуется, обрезается по краям и не может быть пустым
- допускаются arbitrary params под конкретный метод, но на уровне use-case должна быть дополнительная семантическая проверка

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

Валидации:

- `rules` должны ссылаться на уникальные колонки

### `AnonymizeRunResponse`

- `upload_id: str`
- `file_name: str`
- `row_count: int`
- `column_count: int`
- `result_format: ResultFormat = csv_base64`
- `content_base64: str`
- `applied_rules: list[AnonymizationRule]`
- `warnings: list[str]`

Использование:

- ответ `POST /anonymize/run`

Примечание:

- имя выходного файла генерирует backend
- результат анонимизации всегда один CSV-файл

## `src/sda/web/schemas/similar.py`

### `SimilarAnalyzeRequest`

- `preview_rows_limit: int = 5`
- `has_header: bool = true`
- `delimiter: str = ","`

Использование:

- формальная схема для полей формы без файла в `multipart/form-data` запросе `POST /similar/analyze`

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

Валидации:

- `target_rows` в диапазоне `1..10000`

### `SimilarRunResponse`

- `analysis_id: str`
- `file_name: str`
- `row_count: int`
- `column_count: int`
- `result_format: ResultFormat = csv_base64`
- `content_base64: str`
- `warnings: list[str]`

Использование:

- ответ `POST /similar/run`

Примечание:

- имя выходного файла генерирует backend
- результат Similar всегда один CSV-файл

## Общая ошибка

### `ErrorResponse`

- `error_code: str`
- `message: str`
- `details: dict[str, Any] | None`
- `request_id: str | None`

Использование:

- единая структура 4xx/5xx ответов для всех endpoint’ов

## Что важно для роутеров

- Схемы Generate/Anonymize/Similar можно импортировать напрямую в FastAPI-роутеры.
- Для upload endpoints сам файл будет приниматься через `UploadFile`, а остальные поля формы могут маппиться в schema вручную.
- Семантические проверки, зависящие от содержимого CSV или наличия `upload_id`/`analysis_id`, остаются на уровне use-case, а не Pydantic.
