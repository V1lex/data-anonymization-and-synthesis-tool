from datetime import datetime, timedelta
from random import Random


def postprocess_similar_rows(
    rows: list[dict[str, str]],
    *,
    header: list[str],
) -> tuple[list[dict[str, str]], list[str]]:
    if not rows:
        return rows, []

    seeded_random = Random(f"similar::{','.join(header)}::{len(rows)}")
    warnings: list[str] = []
    normalized_header = {name.lower(): name for name in header}

    _apply_date_constraints(rows, normalized_header)
    _apply_ticket_constraints(rows, normalized_header, seeded_random)
    _apply_payment_constraints(rows, normalized_header, seeded_random)
    _apply_quantity_constraints(rows, normalized_header, seeded_random)
    if _apply_currency_price_constraints(rows, normalized_header):
        warnings.append("К полям currency/price применена пост-обработка для более правдоподобных значений.")

    return rows, warnings


def _apply_date_constraints(rows: list[dict[str, str]], header_map: dict[str, str]) -> None:
    birth_key = _find_column(header_map, ("birth_date", "dob"))
    registration_key = _find_column(header_map, ("registration_date", "registered_at", "signup_date"))
    order_key = _find_column(header_map, ("order_date", "ordered_at"))
    payment_key = _find_column(header_map, ("payment_date", "paid_at"))
    created_key = _find_column(header_map, ("created_at",))

    for row in rows:
        registration_date = _parse_date(row.get(registration_key)) if registration_key else None
        birth_date = _parse_date(row.get(birth_key)) if birth_key else None
        order_date = _parse_date(row.get(order_key)) if order_key else None
        payment_date = _parse_date(row.get(payment_key)) if payment_key else None
        created_date = _parse_date(row.get(created_key)) if created_key else None

        if birth_key and registration_key and birth_date and registration_date and birth_date >= registration_date:
            row[birth_key] = (registration_date - timedelta(days=365 * 18)).date().isoformat()
        if registration_key and order_key and registration_date and order_date and order_date < registration_date:
            row[order_key] = registration_date.isoformat()
        if order_key and payment_key and order_date and payment_date and payment_date < order_date:
            row[payment_key] = order_date.isoformat()
        if registration_key and created_key and registration_date and created_date and created_date < registration_date:
            row[created_key] = registration_date.isoformat()


def _apply_ticket_constraints(rows: list[dict[str, str]], header_map: dict[str, str], seeded_random: Random) -> None:
    status_key = _find_column(header_map, ("status",))
    priority_key = _find_column(header_map, ("priority",))
    operator_key = _find_column(header_map, ("operator_name", "agent_name"))
    if operator_key is None and priority_key is None and status_key is None:
        return

    operators = []
    if operator_key:
        for row in rows:
            value = row.get(operator_key, "").strip()
            if value and value not in operators:
                operators.append(value)
            if len(operators) >= min(10, max(1, len(rows) // 20 + 1)):
                break
    if operator_key and not operators:
        operators = ["Operator A", "Operator B", "Operator C"]

    for index, row in enumerate(rows):
        if status_key and row.get(status_key) in {"new", "in progress", "resolved", "closed"}:
            row[status_key] = _weighted_choice(
                seeded_random,
                [("resolved", 0.28), ("closed", 0.24), ("new", 0.24), ("in progress", 0.24)],
            )
        if priority_key and row.get(priority_key) in {"low", "medium", "high"}:
            row[priority_key] = _weighted_choice(
                seeded_random,
                [("low", 0.44), ("medium", 0.41), ("high", 0.15)],
            )
        if operator_key and operators:
            row[operator_key] = operators[index % len(operators)]


def _apply_payment_constraints(rows: list[dict[str, str]], header_map: dict[str, str], seeded_random: Random) -> None:
    status_key = _find_column(header_map, ("status", "payment_status"))
    if status_key is None:
        return
    for row in rows:
        value = row.get(status_key, "").strip().lower()
        if value in {"success", "pending", "failed"}:
            row[status_key] = _weighted_choice(
                seeded_random,
                [("success", 0.88), ("pending", 0.08), ("failed", 0.04)],
            )


def _apply_quantity_constraints(rows: list[dict[str, str]], header_map: dict[str, str], seeded_random: Random) -> None:
    quantity_key = _find_column(header_map, ("amount", "quantity", "qty", "count"))
    if quantity_key is None:
        return
    if not all(_looks_like_int(row.get(quantity_key, "")) for row in rows if row.get(quantity_key, "").strip()):
        return

    for row in rows:
        row[quantity_key] = str(
            _weighted_choice(
                seeded_random,
                [(1, 0.56), (2, 0.2), (3, 0.1), (4, 0.06), (5, 0.04), (6, 0.02), (10, 0.015), (20, 0.005)],
            )
        )


def _apply_currency_price_constraints(rows: list[dict[str, str]], header_map: dict[str, str]) -> bool:
    currency_key = _find_column(header_map, ("currency",))
    price_key = _find_column(header_map, ("price", "cost", "total"))
    if currency_key is None or price_key is None:
        return False

    changed = False
    for row in rows:
        currency = row.get(currency_key, "").strip().upper()
        price = row.get(price_key, "").strip().replace(",", ".")
        if currency not in {"RUB", "USD"}:
            continue
        try:
            numeric_price = float(price)
        except ValueError:
            continue

        if currency == "USD" and numeric_price > 2000:
            row[price_key] = _format_number(max(5.0, numeric_price / 80.0))
            changed = True
        elif currency == "RUB" and numeric_price < 100:
            row[price_key] = _format_number(max(100.0, numeric_price * 80.0))
            changed = True

    return changed


def _find_column(header_map: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in header_map:
            return header_map[candidate]
    return None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for normalized in (value, value.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(normalized).replace(tzinfo=None)
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _looks_like_int(value: str) -> bool:
    stripped = value.strip()
    return stripped.isdigit() or (stripped.startswith("-") and stripped[1:].isdigit())


def _weighted_choice(seeded_random: Random, weighted_items: list[tuple[str | int, float]]) -> str | int:
    threshold = seeded_random.random()
    total = 0.0
    for value, weight in weighted_items:
        total += weight
        if threshold <= total:
            return value
    return weighted_items[-1][0]


def _format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")
