# API-контракты Sprint 1

Документ фиксирует HTTP-контракты для веток `Generate`, `Anonymize` и `Similar`. Контракт рассчитан на синхронный API без отдельного слоя фоновых задач: клиент получает JSON и при необходимости сразу собирает скачиваемый CSV или ZIP из `base64`.

## Общие правила

- Базовый префикс API: `/api/v1`
- Формат успешных ответов: `application/json`
- Формат ошибок: `application/json`
- Кодировка CSV upload/download: `utf-8`
- Все идентификаторы `upload_id` и `analysis_id` считаются временными идентификаторами для одного пользовательского сценария.
- Для бинарных результатов используется `base64` внутри JSON, потому что отдельных download endpoint’ов в Sprint 1 нет.
- Общие лимиты Generate:
  - `row_count` для одного файла: `1..10000`
  - если запрошен один шаблон, backend возвращает один CSV в `content_base64`
  - если запрошено несколько шаблонов, backend возвращает ZIP-архив в `archive_base64`
- Общие методы анонимизации в Sprint 1:
  - `keep`
  - `mask`
  - `redact`
  - `pseudonymize`
  - `generalize_date`

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

- Метод: `GET`
- Путь: `/health`
- Тело запроса: нет

Ответ `200 OK`:

```json
{
  "status": "ok"
}
```

Ошибки:

- `500 internal_error` - сервис не может вернуть health-check.

## GET /generate/templates

- Метод: `GET`
- Путь: `/generate/templates`
- Тело запроса: нет

Ответ `200 OK`:

```json
{
  "items": [
    {
      "template_id": "users",
      "name": "Users",
      "description": "Synthetic user profiles for demo datasets.",
      "preview_columns": ["user_id", "first_name", "last_name", "email"]
    },
    {
      "template_id": "orders",
      "name": "Orders",
      "description": "Synthetic order history linked to users.",
      "preview_columns": ["order_id", "user_id", "order_date", "status"]
    },
    {
      "template_id": "payments",
      "name": "Payments",
      "description": "Synthetic payment transactions linked to orders.",
      "preview_columns": ["payment_id", "order_id", "amount", "payment_status"]
    },
    {
      "template_id": "products",
      "name": "Products",
      "description": "Synthetic product catalog.",
      "preview_columns": ["product_id", "product_name", "category", "price"]
    },
    {
      "template_id": "support_tickets",
      "name": "Support tickets",
      "description": "Synthetic support communication records.",
      "preview_columns": ["ticket_id", "user_id", "topic", "status"]
    }
  ]
}
```

Ошибки:

- `500 internal_error` - не удалось загрузить встроенные template definitions.

## GET /generate/templates/{template_id}

- Метод: `GET`
- Путь: `/generate/templates/{template_id}`
- Параметры пути:
  - `template_id`: `users | orders | payments | products | support_tickets`

Ответ `200 OK`:

```json
{
  "template_id": "users",
  "name": "Users",
  "description": "Synthetic user profiles for demo datasets.",
  "preview_columns": ["user_id", "first_name", "last_name", "email"],
  "columns": [
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

- Метод: `POST`
- Путь: `/generate/run`
- Content-Type: `application/json`

Тело запроса:

```json
{
  "items": [
    {
      "template_id": "users",
      "row_count": 100
    },
    {
      "template_id": "orders",
      "row_count": 100
    }
  ]
}
```

Правила:

- `items` - минимум 1 и максимум 5 шаблонов.
- Один `template_id` нельзя передавать дважды.
- `row_count` на каждый файл должен быть в диапазоне `1..10000`.
- Если в `items` один шаблон, backend возвращает один CSV.
- Если в `items` больше одного шаблона, backend возвращает ZIP-архив.

Ответ `200 OK`:

Вариант 1, один шаблон:

```json
{
  "result_format": "csv_base64",
  "file_name": "users.csv",
  "generated_files": [
    {
      "template_id": "users",
      "file_name": "users.csv",
      "row_count": 100,
      "content_type": "text/csv"
    }
  ],
  "content_base64": "dXNlcl9pZCxlbWFpbA0K...",
  "archive_base64": null,
  "total_rows": 100,
  "warnings": []
}
```

Вариант 2, несколько шаблонов:

```json
{
  "result_format": "zip_base64",
  "file_name": "generated_bundle.zip",
  "generated_files": [
    {
      "template_id": "users",
      "file_name": "users.csv",
      "row_count": 100,
      "content_type": "text/csv"
    },
    {
      "template_id": "orders",
      "file_name": "orders.csv",
      "row_count": 100,
      "content_type": "text/csv"
    }
  ],
  "content_base64": null,
  "archive_base64": "UEsDBBQAAAAI...",
  "total_rows": 200,
  "warnings": []
}
```

Ошибки:

- `400 invalid_template_id` - передан неизвестный template_id.
- `422 validation_error` - нарушены лимиты `row_count` или структура body.
- `500 generation_failed` - генератор не смог построить CSV.

## POST /anonymize/upload

- Метод: `POST`
- Путь: `/anonymize/upload`
- Content-Type: `multipart/form-data`

Поля формы:

- `file`: CSV-файл, обязательный.
- `delimiter`: необязательное поле, 1 символ, по умолчанию `,`.
- `has_header`: необязательный boolean, по умолчанию `true`.
- `suggest`: необязательный boolean, по умолчанию `true`.

Решение по `suggest`: отдельный endpoint не нужен для Sprint 1. Подсказки PII интегрируются в `/anonymize/upload`, чтобы после загрузки клиент сразу получил колонки и предложенные методы. При этом в документе фиксируем, что позже можно добавить отдельный `POST /suggest/rules`, если подсказки потребуется вызывать повторно без повторной загрузки файла.

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

- Метод: `POST`
- Путь: `/anonymize/run`
- Content-Type: `application/json`

Тело запроса:

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
      "method": "generalize_date",
      "params": {}
    }
  ]
}
```

Правила:

- `upload_id` должен ссылаться на ранее загруженный файл.
- `rules` содержит уникальные `column_name`.
- Поддерживаемые методы: `keep`, `mask`, `redact`, `pseudonymize`, `generalize_date`.
- Если колонка не передана в `rules`, backend трактует ее как `keep` только если это явно согласовано в реализации. Для Sprint 1 рекомендуется, чтобы frontend отправлял правила для всех колонок.

Ответ `200 OK`:

```json
{
  "upload_id": "upl_123",
  "file_name": "customers_anonymized.csv",
  "row_count": 850,
  "column_count": 6,
  "result_format": "csv_base64",
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
- `422 validation_error` - дубликаты колонок, пустые имена или невалидная структура body.
- `500 anonymization_failed` - ошибка применения правил.

## POST /similar/analyze

- Метод: `POST`
- Путь: `/similar/analyze`
- Content-Type: `multipart/form-data`

Поля формы:

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

- Метод: `POST`
- Путь: `/similar/run`
- Content-Type: `application/json`

Тело запроса:

```json
{
  "analysis_id": "ana_123",
  "target_rows": 500
}
```

Правила:

- `analysis_id` должен ссылаться на результат `/similar/analyze`.
- `target_rows`: `1..10000`.
- Результат всегда один CSV-файл.

Ответ `200 OK`:

```json
{
  "analysis_id": "ana_123",
  "file_name": "orders_similar.csv",
  "row_count": 500,
  "column_count": 4,
  "result_format": "csv_base64",
  "content_base64": "c3RhdHVzLHRvdGFsX2Ftb3VudA0K...",
  "warnings": []
}
```

Ошибки:

- `404 analysis_not_found` - `analysis_id` не найден или истек.
- `400 invalid_target_rows` - `target_rows` вне допустимого диапазона.
- `422 validation_error` - невалидный JSON/body.
- `500 synthesis_failed` - генерация похожего CSV не завершилась.
