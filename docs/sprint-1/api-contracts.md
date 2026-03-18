# API-контракты спринта 1 (MVP)

## 1. Общие правила
1. Базовый префикс API: `/api/v1` (или проектный префикс, если настроен иначе).
2. Успешный ответ для файловых endpoint'ов: `200` + `text/csv`.
3. Ошибки валидации: `422`; доменные ошибки: `400`.
4. Неверный HTTP-метод: `405`.

## 2. Эндпоинты
### 2.1 Проверка здоровья
`GET /health`

Успех `200`:
```json
{
  "status": "ok"
}
```

### 2.2 Генерация CSV
`POST /generate`

Пример запроса:
```json
{
  "template": "users",
  "rows": 100,
  "delimiter": ",",
  "seed": 42
}
```

Успех `200`:
1. `Content-Type: text/csv`.
2. `Content-Disposition: attachment; filename="<template>.csv"`.
3. Тело ответа: CSV-байты.

Ошибки:
1. Неизвестный шаблон -> `400/422`.
2. `rows <= 0` -> `400/422`.
3. Некорректный `delimiter` -> `400/422`.

### 2.3 Анонимизация CSV
`POST /anonymize`

Запрос:
1. `multipart/form-data`.
2. Поле `file`: CSV-файл.
3. Поле `rules`: JSON-объект (`колонка -> метод`).

Пример `rules`:
```json
{
  "email": { "method": "mask" },
  "phone": { "method": "redact" },
  "full_name": { "method": "pseudo" },
  "city": { "method": "keep" }
}
```

Успех `200`:
1. `Content-Type: text/csv`.
2. `Content-Disposition: attachment; filename="anonymized.csv"`.
3. Тело ответа: анонимизированный CSV.

Ошибки:
1. Пустой или поврежденный CSV -> `400/422`.
2. Неизвестная колонка в `rules` -> `400/422`.
3. Неподдерживаемый `method` -> `400/422`.

### 2.4 Подсказка PII (вспомогательный endpoint)
`POST /suggest`

Запрос:
1. `multipart/form-data`.
2. Поле `file`: CSV-файл.

Успех `200`:
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

Примечания:
1. Подсказки носят рекомендательный характер.
2. Для колонок без правила используется `keep`.

### 2.5 Similar/Synthesize (этап после MVP)
`POST /similar`

Статус в спринте 1: черновик контракта, реализация после MVP.

## 3. Формат ошибки
```json
{
  "detail": "читаемое сообщение об ошибке"
}
```

## 4. Контракт скачивания файла
Для `POST /generate` и `POST /anonymize`:
1. Ответ должен скачиваться как `.csv`.
2. Имя файла задается в `Content-Disposition`.
3. Кодировка CSV по умолчанию - UTF-8.
