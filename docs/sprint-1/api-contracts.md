# API Contracts Sprint 1

Документ фиксирует HTTP-контракты для веток `Generate`, `Anonymize` и `Similar`. Контракт задуман как синхронный API без отдельного polling/job-слоя: frontend получает JSON и при необходимости сразу собирает downloadable CSV/ZIP из `base64`.

## Общие правила

- Base URL: `/api/v1`
- Формат успешных ответов: `application/json`
- Формат ошибок: `application/json`
- Кодировка CSV upload/download: `utf-8`
- Все идентификаторы `upload_id` и `analysis_id` считаются временными server-side token’ами для одного сценария работы пользователя.
- Для бинарных результатов используется `base64` внутри JSON, потому что отдельных download endpoint’ов в Sprint 1 нет.

## Общая схема ошибки

```json
{
  "error_code": "validation_error",
  "message": "row_count must be between 1 and 10000",
  "details": {
    "field": "items[0].row_count"
  },
  "request_id": "req_123"
}
```

## GET /health

- Method: `GET`
- Path: `/health`
- Request body: нет

Ответ `200 OK`:

```json
{
  "status": "ok"
}
```

Ошибки:

- `500 internal_error` - сервис не может вернуть health-check.

## GET /generate/templates

- Method: `GET`
- Path: `/generate/templates`
- Request body: нет

Ответ `200 OK`:

```json
{
  "items": [
    {
      "template_id": "users",
      "name": "Users",
      "description": "Synthetic user profiles for demo datasets.",
      "columns": ["user_id", "first_name", "last_name", "email"],
      "default_rows": 100,
      "max_rows": 10000
    }
  ]
}
```

Ошибки:

- `500 internal_error` - не удалось загрузить встроенные template definitions.

## GET /generate/templates/{template_id}

- Method: `GET`
- Path: `/generate/templates/{template_id}`
- Path params:
  - `template_id`: `users | orders | payments | products | support_tickets`

Ответ `200 OK`:

```json
{
  "template_id": "users",
  "name": "Users",
  "description": "Synthetic user profiles for demo datasets.",
  "columns": ["user_id", "first_name", "last_name", "email"],
  "default_rows": 100,
  "max_rows": 10000,
  "recommended_rows": [100, 500, 1000, 5000],
  "relations": ["orders.user_id -> users.user_id"],
  "columns_detail": [
    {
      "name": "email",
      "description": "User email address",
      "example_value": "alex@example.com",
      "pii_expected": true
    }
  ]
}
```

Ошибки:

- `404 template_not_found` - template_id не существует.
- `500 internal_error` - template metadata не удалось прочитать.

## POST /generate/run

- Method: `POST`
- Path: `/generate/run`
- Content-Type: `application/json`

Request body:

```json
{
  "items": [
    {
      "template_id": "users",
      "row_count": 100,
      "file_name": "users.csv"
    },
    {
      "template_id": "orders",
      "row_count": 100,
      "file_name": "orders.csv"
    }
  ],
  "result_format": "zip_base64",
  "random_seed": 42
}
```

Правила:

- `items` - минимум 1 и максимум 5 шаблонов.
- Один `template_id` нельзя передавать дважды.
- `row_count` на файл: `1..10000`.
- `result_format=csv_base64` допустим только если в `items` ровно один шаблон.

Ответ `200 OK`:

```json
{
  "result_format": "zip_base64",
  "file_name": "generated_bundle.zip",
  "generated_files": [
    {
      "template_id": "users",
      "file_name": "users.csv",
      "row_count": 100,
      "content_base64": "dXNlcl9pZCxlbWFpbA0K...",
      "content_type": "text/csv"
    }
  ],
  "archive_base64": "UEsDBBQAAAAI...",
  "total_rows": 200,
  "warnings": []
}
```

Ошибки:

- `400 invalid_template_id` - передан неизвестный template_id.
- `400 invalid_result_format` - конфликт между `result_format` и количеством файлов.
- `422 validation_error` - нарушены лимиты `row_count`, `file_name` или структуры body.
- `500 generation_failed` - генератор не смог построить CSV.

## POST /anonymize/upload

- Method: `POST`
- Path: `/anonymize/upload`
- Content-Type: `multipart/form-data`

Form fields:

- `file`: CSV-файл, обязательный.
- `delimiter`: optional, 1 символ, по умолчанию `,`.
- `has_header`: optional boolean, по умолчанию `true`.
- `suggest`: optional boolean, по умолчанию `true`.

Решение по `suggest`: отдельный endpoint не нужен для Sprint 1. Подсказки PII интегрируются в `/anonymize/upload`, чтобы после upload frontend сразу получил columns + suggested methods и не ждал второй round trip.

Ответ `200 OK`:

```json
{
  "upload_id": "upl_123",
  "file_name": "customers.csv",
  "row_count": 850,
  "column_count": 6,
  "columns": [
    {
      "index": 0,
      "name": "email",
      "inferred_type": "string",
      "sample_values": ["a@example.com", "b@example.com"],
      "null_ratio": 0.0,
      "unique_ratio": 0.99,
      "suggested_method": "mask",
      "suggestion_confidence": 0.95,
      "pii_hint": "column name and sample values look like email"
    }
  ],
  "preview_rows": [
    {
      "email": "a@example.com",
      "city": "Moscow"
    }
  ],
  "delimiter": ",",
  "encoding": "utf-8",
  "suggestions_included": true,
  "warnings": []
}
```

Ошибки:

- `400 invalid_file_type` - загружен не CSV.
- `400 empty_file` - файл пустой.
- `400 csv_parse_error` - CSV не удалось разобрать.
- `413 file_too_large` - превышен лимит по размеру файла.
- `422 validation_error` - слишком много строк/колонок или некорректный `delimiter`.
- `500 upload_processing_failed` - внутренняя ошибка анализа файла.

## POST /anonymize/run

- Method: `POST`
- Path: `/anonymize/run`
- Content-Type: `application/json`

Request body:

```json
{
  "upload_id": "upl_123",
  "rules": [
    {
      "column_name": "email",
      "method": "mask",
      "params": {
        "keep_domain": true
      }
    },
    {
      "column_name": "birth_date",
      "method": "generalize_year",
      "params": {}
    }
  ],
  "output_format": "csv_base64",
  "file_name": "customers_anonymized.csv"
}
```

Правила:

- `upload_id` должен ссылаться на ранее загруженный файл.
- `rules` содержит уникальные `column_name`.
- Метод `remove` удаляет колонку из результата.
- Если колонка не передана в `rules`, backend трактует ее как `keep` только если это явно согласовано в реализации; для Sprint 1 рекомендуется frontend отправлять все колонки.

Ответ `200 OK`:

```json
{
  "upload_id": "upl_123",
  "file_name": "customers_anonymized.csv",
  "row_count": 850,
  "column_count": 5,
  "output_format": "csv_base64",
  "content_base64": "ZW1haWwsY2l0eQ0K...",
  "applied_rules": [
    {
      "column_name": "email",
      "method": "mask",
      "params": {
        "keep_domain": true
      }
    }
  ],
  "warnings": []
}
```

Ошибки:

- `404 upload_not_found` - `upload_id` не найден или истек.
- `400 unknown_column` - правило ссылается на отсутствующую колонку.
- `400 invalid_rule` - метод не поддерживается для типа колонки.
- `422 validation_error` - дубликаты колонок, пустые имена, неверный `file_name`.
- `500 anonymization_failed` - ошибка применения правил.

## POST /similar/analyze

- Method: `POST`
- Path: `/similar/analyze`
- Content-Type: `multipart/form-data`

Form fields:

- `file`: CSV-файл, обязательный.
- `preview_rows_limit`: optional integer, по умолчанию `5`, диапазон `1..20`.
- `has_header`: optional boolean, по умолчанию `true`.
- `delimiter`: optional, 1 символ, по умолчанию `,`.

Ответ `200 OK`:

```json
{
  "analysis_id": "ana_123",
  "file_name": "orders.csv",
  "row_count": 1200,
  "column_count": 4,
  "columns": [
    {
      "name": "status",
      "inferred_type": "category",
      "null_ratio": 0.0,
      "unique_ratio": 0.01,
      "sample_values": ["new", "paid", "cancelled"]
    }
  ],
  "preview_rows": [
    {
      "status": "paid",
      "total_amount": "120.00"
    }
  ],
  "summary": [
    "4 columns detected",
    "1 numeric column with positive range",
    "1 low-cardinality categorical column"
  ],
  "warnings": []
}
```

Ошибки:

- `400 invalid_file_type` - загружен не CSV.
- `400 empty_file` - файл пустой.
- `400 csv_parse_error` - файл невозможно проанализировать.
- `413 file_too_large` - превышен лимит входного файла.
- `422 validation_error` - нарушены лимиты по `preview_rows_limit`, строкам или колонкам.
- `500 analysis_failed` - внутренняя ошибка анализа структуры.

## POST /similar/run

- Method: `POST`
- Path: `/similar/run`
- Content-Type: `application/json`

Request body:

```json
{
  "analysis_id": "ana_123",
  "target_rows": 500,
  "output_format": "csv_base64",
  "random_seed": 42,
  "file_name": "orders_similar.csv"
}
```

Правила:

- `analysis_id` должен ссылаться на результат `/similar/analyze`.
- `target_rows`: `1..10000`.
- Sprint 1 использует только `csv_base64`.

Ответ `200 OK`:

```json
{
  "analysis_id": "ana_123",
  "file_name": "orders_similar.csv",
  "row_count": 500,
  "column_count": 4,
  "output_format": "csv_base64",
  "content_base64": "c3RhdHVzLHRvdGFsX2Ftb3VudA0K...",
  "warnings": []
}
```

Ошибки:

- `404 analysis_not_found` - `analysis_id` не найден или истек.
- `400 invalid_target_rows` - `target_rows` вне допустимого диапазона.
- `422 validation_error` - невалидный JSON/body.
- `500 synthesis_failed` - генерация похожего CSV не завершилась.
