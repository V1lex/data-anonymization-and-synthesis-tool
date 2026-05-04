# Финальный test report T044

**Дата:** 4 мая 2026
**Проверил:** Андрей
**Цель проверки:** финальная регрессия основных сценариев SDA

## Итог

Generate и Anonymize прошли функциональную проверку и готовы к использованию.
Backend unit tests прошли полностью: 85 из 85.

Similar прошёл проверку анализа исходного CSV и генерации похожего датасета.

## 1. Unit tests

```text
============================= test session starts ==============================
collected 85 items
=============================== 85 passed in 12.34s ==============================
```

Проверенные наборы тестов:

- `test_anonymize.py` - 12 тестов
- `test_anonymizer.py` - 5 тестов
- `test_api_anonymize.py` - 7 тестов
- `test_api_generate.py` - 6 тестов
- `test_api_similar.py` - 4 теста
- `test_csv_io.py` - 10 тестов
- `test_field_detector.py` - 8 тестов
- `test_generate.py` - 6 тестов
- `test_generator.py` - 8 тестов
- `test_generator_relations.py` - 3 теста
- `test_semantic_consistency.py` - 4 теста
- `test_suggester.py` - 5 тестов
- `test_synthesis.py` - 3 теста
- `test_upload_store.py` - 3 теста

## 2. Integration tests

Всего проверено 8 интеграционных сценариев. Все сценарии прошли успешно.

### 2.1 Generate

#### Health check

```bash
GET /api/v1/health
```

Результат: PASS

- Status: 200 OK
- Response: `{"status": "ok"}`

#### Получение шаблонов

```bash
GET /api/v1/generate/templates
```

Результат: PASS

- Status: 200 OK
- Доступно 5 шаблонов: `users`, `products`, `orders`, `payments`, `support_tickets`

#### Генерация одного шаблона

```bash
POST /api/v1/generate/run
{
  "items": [{"template_id": "users", "row_count": 5}],
  "locale": "en_US"
}
```

Результат: PASS

- Status: 200 OK
- Сформирован CSV в base64
- Возвращены колонки: `user_id`, `full_name`, `email`, `phone`, `city`, `address`, `birth_date`, `registration_date`

#### Генерация связанных таблиц

```bash
POST /api/v1/generate/run
{
  "items": [
    {"template_id": "users", "row_count": 3},
    {"template_id": "products", "row_count": 2},
    {"template_id": "orders", "row_count": 3},
    {"template_id": "payments", "row_count": 3},
    {"template_id": "support_tickets", "row_count": 2}
  ],
  "locale": "en_US"
}
```

Результат: PASS

- Status: 200 OK
- Сформирован ZIP-архив с таблицами
- Связи между таблицами сохранены
- Данные сгенерированы для локали `en_US`

### 2.2 Anonymize

#### Загрузка CSV

```bash
POST /api/v1/anonymize/upload
Body: multipart/form-data with test.csv
```

Результат: PASS

- Status: 200 OK
- Файл принят и сохранен в сессии
- Определены колонки: `name`, `email`, `phone`, `birth_date`
- Для персональных полей предложены правила анонимизации

#### Применение правил анонимизации

```bash
POST /api/v1/anonymize/run
{
  "upload_id": "generated_id",
  "rules": [
    {"column_name": "name", "method": "keep"},
    {"column_name": "email", "method": "mask"},
    {"column_name": "phone", "method": "mask"},
    {"column_name": "birth_date", "method": "generalize_year"}
  ]
}
```

Результат: PASS

- Status: 200 OK
- Сформирован итоговый CSV
- `name` оставлен без изменений
- `email` и `phone` замаскированы
- `birth_date` обобщен до года

### 2.3 Similar

#### Анализ датасета

```bash
POST /api/v1/similar/analyze
Body: multipart/form-data with test.csv
```

Результат: PASS

- Status: 200 OK
- Сформирован `analysis_id`
- Определены колонки исходного CSV
- Сформированы summary, warnings и preview rows

#### Генерация похожего датасета

```bash
POST /api/v1/similar/run
{
  "analysis_id": "generated_id",
  "target_rows": 5
}
```

Результат: PASS

- Status: 200 OK
- Сформирован CSV в base64
- Сохранены структура колонок и базовые типы данных

## 3. README и документация

README проверен по актуальным сценариям запуска.

| Раздел | Статус | Комментарий |
|--------|--------|-------------|
| Docker Compose | Актуален | Запускает backend и frontend |
| Локальный запуск backend | Актуален | Backend доступен на `http://127.0.0.1:8000` |
| Локальный запуск frontend | Актуален | Frontend доступен на `http://127.0.0.1:3000` |
| API | Актуален | Основные endpoint'ы указаны корректно |

## 4. Обнаруженные проблемы

Блокирующих проблем по проверенным сценариям не обнаружено.

## 5. Финальная оценка

Generate, Anonymize и Similar готовы к демонстрации и использованию в текущей версии.
