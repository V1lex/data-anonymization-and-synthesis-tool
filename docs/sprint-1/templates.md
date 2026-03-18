# Каталог шаблонов Sprint 1 (MVP)

## 1. Цель
Единый источник правды по шаблонам генерации, используемым в MVP-демо.

## 2. Поддерживаемые шаблоны

### 2.1 `users`
Выходной файл: `users.csv`

Колонки:
1. `user_id`
2. `first_name`
3. `last_name`
4. `full_name`
5. `email`
6. `phone`
7. `city`
8. `address`
9. `birth_date`
10. `registration_date`
11. `is_active`

### 2.2 `orders`
Выходной файл: `orders.csv`

Колонки:
1. `order_id`
2. `user_id`
3. `order_date`
4. `status`
5. `total_amount`
6. `currency`
7. `delivery_city`
8. `delivery_address`
9. `comment`

### 2.3 `payments`
Выходной файл: `payments.csv`

Колонки:
1. `payment_id`
2. `order_id`
3. `user_id`
4. `payment_date`
5. `amount`
6. `payment_method`
7. `payment_status`
8. `transaction_reference`
9. `payer_email`

### 2.4 `products`
Выходной файл: `products.csv`

Колонки:
1. `product_id`
2. `product_name`
3. `category`
4. `price`
5. `brand`
6. `supplier_name`
7. `created_at`
8. `is_available`

### 2.5 `support_tickets`
Выходной файл: `support_tickets.csv`

Колонки:
1. `ticket_id`
2. `user_id`
3. `created_at`
4. `topic`
5. `message_text`
6. `channel`
7. `status`
8. `priority`
9. `operator_name`
10. `contact_email`

## 3. Где хранятся шаблоны
1. `src/sda/resources/templates/users.json`
2. `src/sda/resources/templates/orders.json`
3. `src/sda/resources/templates/payments.json`
4. `src/sda/resources/templates/products.json`
5. `src/sda/resources/templates/support_tickets.json`

## 4. Ограничения MVP
1. Имена шаблонов чувствительны к регистру.
2. Неизвестный шаблон должен возвращать ошибку валидации.
3. Порядок колонок на выходе строго совпадает с описанием шаблона.
