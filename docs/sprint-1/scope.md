# Scope Sprint 1: границы MVP

## Цель документа
Зафиксировать, что входит в Показ 1 (MVP), а что переносится в post-MVP.

## Продуктовые ветки
1. `Generate`
2. `Anonymize`
3. `Similar`

## Generate (входит в MVP)
### Что делает пользователь
1. Выбирает одну или несколько таблиц для генерации.
2. Указывает количество строк.
3. Скачивает CSV-файл(ы).

### Шаблоны и колонки в MVP
1. `users.csv`
- `user_id`
- `first_name`
- `last_name`
- `full_name`
- `email`
- `phone`
- `city`
- `address`
- `birth_date`
- `registration_date`
- `is_active`

2. `orders.csv`
- `order_id`
- `user_id`
- `order_date`
- `status`
- `total_amount`
- `currency`
- `delivery_city`
- `delivery_address`
- `comment`

3. `payments.csv`
- `payment_id`
- `order_id`
- `user_id`
- `payment_date`
- `amount`
- `payment_method`
- `payment_status`
- `transaction_reference`
- `payer_email`

4. `products.csv`
- `product_id`
- `product_name`
- `category`
- `price`
- `brand`
- `supplier_name`
- `created_at`
- `is_available`

5. `support_tickets.csv`
- `ticket_id`
- `user_id`
- `created_at`
- `topic`
- `message_text`
- `channel`
- `status`
- `priority`
- `operator_name`
- `contact_email`

## Anonymize (входит в MVP)
### Что делает пользователь
1. Загружает произвольный CSV.
2. Получает анализ колонок.
3. Выбирает способ обработки для каждой колонки.
4. Скачивает анонимизированный CSV.

### Что входит в MVP
1. Работа с произвольным CSV, а не только с фиксированными шаблонами.
2. Сценарий: загрузка -> анализ -> настройка правил -> скачивание.
3. Значение по умолчанию для колонок без правил: `keep`.
4. Поддержка `suggest_pii` как вспомогательной подсказки.
5. Стабильный демо-сценарий на типовых наборах данных.

## Similar (post-MVP, не входит в Показ 1)
### Что делает пользователь
1. Загружает CSV.
2. Система анализирует структуру и простые статистики.
3. Пользователь скачивает похожий synthetic CSV.

### Что включает фича
1. Анализ схемы (колонки/типы) и базовых статистик.
2. Генерация «похожего» датасета с сохранением структуры.
3. Экспорт результата в CSV.

## Разделение по этапам
### Sprint 1 / Показ 1
1. Рабочие ветки: `Generate`, `Anonymize`.
2. Демо-сценарии:
- Generate: выбор шаблона + rows -> скачивание CSV.
- Anonymize: загрузка CSV -> анализ (+ suggest) -> ручная настройка -> скачивание.

### Post-MVP (Sprint 3+)
1. Полноценная реализация ветки `Similar`.
2. Повышение качества synthetic-генерации.
3. Расширение покрытия edge-cases и UX.
