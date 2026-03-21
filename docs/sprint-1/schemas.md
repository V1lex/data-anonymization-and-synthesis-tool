# Схемы Sprint 1 (MVP)

## 1. Схема запроса `generate`
```json
{
  "template": "string, required",
  "rows": "integer, required, > 0",
  "delimiter": "string, optional, default ','",
  "seed": "integer, optional"
}
```

## 2. Схема `rules` для `anonymize`
```json
{
  "<column_name>": {
    "method": "keep | mask | redact | pseudo | generalize_date",
    "params": {}
  }
}
```

Правила:
1. `params` опционален и зависит от метода.
2. Для колонок без правила применяется `keep`.
3. Неизвестная колонка вызывает ошибку валидации.

## 3. Схема ответа `suggest`
```json
{
  "columns": [
    {
      "name": "string",
      "suggested_method": "keep | mask | redact | pseudo | generalize_date",
      "confidence": "number from 0 to 1",
      "reason": "string"
    }
  ]
}
```

## 4. Базовая схема ошибки
```json
{ "detail": "string" }
```
