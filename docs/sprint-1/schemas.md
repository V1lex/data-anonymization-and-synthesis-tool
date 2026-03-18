# Схемы спринта 1 (MVP)

## 1. Схема запроса генерации
```json
{
  "template": "строка, обязательно",
  "rows": "целое число, обязательно, > 0",
  "delimiter": "строка, необязательно, по умолчанию ','",
  "seed": "целое число, необязательно"
}
```

Проверки:
1. `template` должен входить в список поддерживаемых.
2. `rows` должен быть положительным.
3. `delimiter` должен быть одиночным символом-разделителем CSV.

## 2. Схема правил анонимизации
```json
{
  "<column_name>": {
    "method": "keep | mask | redact | pseudo",
    "params": {}
  }
}
```

Пояснения:
1. `params` необязателен и зависит от метода.
2. Если правило не задано, используется `keep`.
3. Неизвестная колонка в `rules` должна вызывать ошибку валидации.

## 3. Схема ответа подсказок
```json
{
  "columns": [
    {
      "name": "строка",
      "suggested_method": "keep | mask | redact | pseudo",
      "confidence": "число от 0 до 1",
      "reason": "строка"
    }
  ]
}
```

## 4. Схемы CSV на выходе
1. `users.csv`: `user_id`, `first_name`, `last_name`, `full_name`, `email`, `phone`, `city`, `address`, `birth_date`, `registration_date`, `is_active`.
2. `orders.csv`: `order_id`, `user_id`, `order_date`, `status`, `total_amount`, `currency`, `delivery_city`, `delivery_address`, `comment`.
3. `payments.csv`: `payment_id`, `order_id`, `user_id`, `payment_date`, `amount`, `payment_method`, `payment_status`, `transaction_reference`, `payer_email`.
4. `products.csv`: `product_id`, `product_name`, `category`, `price`, `brand`, `supplier_name`, `created_at`, `is_available`.
5. `support_tickets.csv`: `ticket_id`, `user_id`, `created_at`, `topic`, `message_text`, `channel`, `status`, `priority`, `operator_name`, `contact_email`.

## 5. Базовая схема ошибки
```json
{
  "detail": "строка"
}
```

Расширение (необязательно):
```json
{
  "detail": "строка",
  "code": "строка",
  "field": "строка"
}
```
