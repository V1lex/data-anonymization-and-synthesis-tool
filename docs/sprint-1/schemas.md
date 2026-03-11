# Schemas Sprint 1 (MVP)

## 1. Generate Request Schema
```json
{
  "template": "string, required",
  "rows": "integer, required, > 0",
  "delimiter": "string, optional, default ','",
  "seed": "integer, optional"
}
```

Validation:
1. `template` must be one of supported templates.
2. `rows` must be positive.
3. `delimiter` must be a single-character CSV delimiter.

## 2. Anonymize Rules Schema
Rules map:
```json
{
  "<column_name>": {
    "method": "keep | mask | redact | pseudo",
    "params": {}
  }
}
```

Rules notes:
1. `params` is optional and method-specific.
2. If column has no explicit rule, default is `keep`.
3. Unknown column in rules should fail validation.

## 3. Suggest Response Schema
```json
{
  "columns": [
    {
      "name": "string",
      "suggested_method": "keep | mask | redact | pseudo",
      "confidence": "number from 0 to 1",
      "reason": "string"
    }
  ]
}
```

## 4. CSV Output Schemas

### 4.1 users.csv
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

### 4.2 orders.csv
1. `order_id`
2. `user_id`
3. `order_date`
4. `status`
5. `total_amount`
6. `currency`
7. `delivery_city`
8. `delivery_address`
9. `comment`

### 4.3 payments.csv
1. `payment_id`
2. `order_id`
3. `user_id`
4. `payment_date`
5. `amount`
6. `payment_method`
7. `payment_status`
8. `transaction_reference`
9. `payer_email`

### 4.4 products.csv
1. `product_id`
2. `product_name`
3. `category`
4. `price`
5. `brand`
6. `supplier_name`
7. `created_at`
8. `is_available`

### 4.5 support_tickets.csv
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

## 5. Error Schema (baseline)
```json
{
  "detail": "string"
}
```

Optional extension:
```json
{
  "detail": "string",
  "code": "string",
  "field": "string"
}
```
