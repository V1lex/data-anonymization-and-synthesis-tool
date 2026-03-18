# Границы MVP спринта 1

## Цель документа
Зафиксировать, что входит в Показ 1 (MVP), а что переносится на этап после MVP.

## Продуктовые ветки
1. `Generate`
2. `Anonymize`
3. `Similar`

## `Generate` (входит в MVP)
### Действия пользователя
1. Выбирает одну или несколько таблиц для генерации.
2. Указывает количество строк.
3. Скачивает CSV-файл(ы).

### Шаблоны и колонки в MVP
1. `users.csv`: `user_id`, `first_name`, `last_name`, `full_name`, `email`, `phone`, `city`, `address`, `birth_date`, `registration_date`, `is_active`.
2. `orders.csv`: `order_id`, `user_id`, `order_date`, `status`, `total_amount`, `currency`, `delivery_city`, `delivery_address`, `comment`.
3. `payments.csv`: `payment_id`, `order_id`, `user_id`, `payment_date`, `amount`, `payment_method`, `payment_status`, `transaction_reference`, `payer_email`.
4. `products.csv`: `product_id`, `product_name`, `category`, `price`, `brand`, `supplier_name`, `created_at`, `is_available`.
5. `support_tickets.csv`: `ticket_id`, `user_id`, `created_at`, `topic`, `message_text`, `channel`, `status`, `priority`, `operator_name`, `contact_email`.

## `Anonymize` (входит в MVP)
### Действия пользователя
1. Загружает произвольный CSV.
2. Получает анализ колонок.
3. Выбирает способ обработки для каждой колонки.
4. Скачивает анонимизированный CSV.

### Что входит в MVP
1. Работа с произвольным CSV, а не только с фиксированными шаблонами.
2. Сценарий: загрузка -> анализ -> настройка правил -> скачивание.
3. Значение по умолчанию для колонок без правил: `keep`.
4. Поддержка `suggest_pii` как вспомогательной подсказки.

## `Similar` (после MVP, не входит в Показ 1)
1. Загрузка CSV.
2. Анализ структуры и базовых статистик.
3. Генерация и скачивание похожего synthetic CSV.

## Разделение по этапам
### Спринт 1 / Показ 1
1. Рабочие ветки: `Generate`, `Anonymize`.
2. Демо-сценарии: генерация CSV и анонимизация CSV со скачиванием результата.

### Этап после MVP (спринт 3+)
1. Полноценная реализация ветки `Similar`.
2. Повышение качества synthetic-генерации.
3. Расширение покрытия сложных случаев и UX.
