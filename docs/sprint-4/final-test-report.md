# Финальный test report Sprint 4

**Дата обновления:** 5 мая 2026
**Ветка проверки:** `task-T044-final-regression-uat`
**База:** после merge актуального `origin/main`

## Итог

Generate, Anonymize и Similar прошли актуальную автоматическую регрессию.

Backend test suite на последней версии содержит 94 теста. Последний полный прогон:

```text
94 passed in 3.76s
```

Frontend production build также проходит:

```text
npm run build
✓ Compiled successfully
✓ Generating static pages (6/6)
```

## 1. Automated tests

Команда:

```bash
./.venv/bin/python -m pytest -q
```

Результат: PASS

Покрытые наборы тестов:

| Файл | Что проверяет |
|------|---------------|
| `tests/test_anonymize.py` | use case загрузки и применения правил анонимизации |
| `tests/test_anonymizer.py` | базовые методы анонимизации и эвристики |
| `tests/test_api_anonymize.py` | API загрузки CSV и запуска anonymize |
| `tests/test_api_generate.py` | API Generate, домены, зависимости шаблонов, ошибки валидации |
| `tests/test_api_similar.py` | API Similar single-table и multi-table |
| `tests/test_csv_io.py` | чтение/запись CSV, delimiter detection, ошибки структуры |
| `tests/test_field_detector.py` | определение типов колонок и PII |
| `tests/test_generate.py` | use case Generate и ZIP/CSV результат |
| `tests/test_generator.py` | генератор шаблонов, Faker locale, провайдеры |
| `tests/test_generator_relations.py` | связи `users` / `products` / `orders` / `payments` |
| `tests/test_semantic_consistency.py` | доменная консистентность Generate и Similar postprocess |
| `tests/test_suggester.py` | предложения правил анонимизации |
| `tests/test_synthesis.py` | Similar SDV single-table и multi-table synthesis |
| `tests/test_upload_store.py` | файловые session stores и TTL |

## 2. Frontend build

Команда:

```bash
cd frontend
npm run build
```

Результат: PASS

Проверены production build и статическая генерация страниц:

- `/`
- `/anonymize`
- `/generate`
- `/similar`
- `/_not-found`

## 3. Functional coverage

### 3.1 Generate

Актуальные endpoint'ы:

- `GET /api/v1/generate/templates`
- `GET /api/v1/generate/domains`
- `GET /api/v1/generate/templates/{template_id}`
- `POST /api/v1/generate/run`

Проверенное состояние:

- доступно 5 шаблонов: `users`, `products`, `orders`, `payments`, `support_tickets`;
- доступны 6 доменов генерации: `ecommerce`, `fintech`, `shops`, `logistics`, `education`, `crm`;
- домен `shops` описывает продуктовые магазины и генерирует food/grocery products;
- frontend больше не выбирает `products` автоматически;
- одиночный шаблон возвращается как CSV base64;
- несколько связанных шаблонов возвращаются ZIP-архивом;
- зависимости таблиц сохраняются: `orders` связан с `users` и `products`, `payments` связан с `orders`.

### 3.2 Anonymize

Актуальные endpoint'ы:

- `POST /api/v1/anonymize/upload`
- `POST /api/v1/anonymize/run`

Проверенное состояние:

- загрузка CSV определяет колонки, delimiter и preview;
- PII detector распознает email, phone, dates, names, address-like columns и identifiers;
- suggester предлагает методы анонимизации по типам колонок;
- `keep`, `mask`, `redact`, `pseudonymize`, `generalize_year` проходят регрессию;
- некорректные правила возвращают детализированные validation errors.

### 3.3 Similar

Актуальные endpoint'ы:

- `POST /api/v1/similar/analyze`
- `POST /api/v1/similar/run`
- `POST /api/v1/similar/multi/analyze`
- `POST /api/v1/similar/multi/run`

Проверенное состояние single-table Similar:

- один CSV до 5 МБ;
- анализ возвращает `analysis_id`, типы колонок, summary и preview rows;
- генерация возвращает похожий CSV base64;
- сохраняются структура колонок, базовые типы данных и читаемые значения после postprocess.

Проверенное состояние multi-table Similar:

- от 2 до 5 CSV;
- каждый файл до 5 МБ, суммарно до 25 МБ;
- система определяет таблицы, primary keys и foreign keys, когда связи выводимы из данных;
- генерация выполняется через SDV `HMASynthesizer`;
- результат возвращается ZIP-архивом;
- размер результата задается scale от `0.1` до `5`;
- поддержаны как связанные, так и несвязанные наборы таблиц.

## 4. Documentation status

README и sprint-4 документы приведены к текущему состоянию функциональности:

- запуск через Docker Compose;
- локальный запуск backend;
- локальный запуск frontend;
- Generate domains;
- Similar single-table и multi-table flows;
- актуальная команда backend tests;
- актуальная команда frontend build.

## 5. Known status

Блокирующих проблем по автоматической регрессии и production build не обнаружено.

Текущее состояние готово для demo/UAT по Sprint 4.
