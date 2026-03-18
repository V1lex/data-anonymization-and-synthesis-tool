# Каталог шаблонов спринта 1 (MVP)

## 1. Цель
Единый источник информации по шаблонам генерации для MVP-демо.

## 2. Поддерживаемые шаблоны
1. `users` -> `users.csv` с колонками: `user_id`, `first_name`, `last_name`, `full_name`, `email`, `phone`, `city`, `address`, `birth_date`, `registration_date`, `is_active`.
2. `orders` -> `orders.csv` с колонками: `order_id`, `user_id`, `order_date`, `status`, `total_amount`, `currency`, `delivery_city`, `delivery_address`, `comment`.
3. `payments` -> `payments.csv` с колонками: `payment_id`, `order_id`, `user_id`, `payment_date`, `amount`, `payment_method`, `payment_status`, `transaction_reference`, `payer_email`.
4. `products` -> `products.csv` с колонками: `product_id`, `product_name`, `category`, `price`, `brand`, `supplier_name`, `created_at`, `is_available`.
5. `support_tickets` -> `support_tickets.csv` с колонками: `ticket_id`, `user_id`, `created_at`, `topic`, `message_text`, `channel`, `status`, `priority`, `operator_name`, `contact_email`.

## 3. Хранение шаблонов
1. `src/sda/resources/templates/users.json`
2. `src/sda/resources/templates/orders.json`
3. `src/sda/resources/templates/payments.json`
4. `src/sda/resources/templates/products.json`
5. `src/sda/resources/templates/support_tickets.json`

## 4. Ограничения MVP
1. Имена шаблонов чувствительны к регистру.
2. Неизвестный шаблон должен возвращать ошибку валидации.
3. Порядок колонок в CSV строго соответствует шаблону.
