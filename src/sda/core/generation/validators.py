from datetime import UTC, date, datetime, timedelta
from random import Random
from typing import Any

CITY_PROFILES = {
    "ru_RU": [
        ("Москва", 18),
        ("Санкт-Петербург", 13),
        ("Новосибирск", 7),
        ("Екатеринбург", 6),
        ("Казань", 6),
        ("Нижний Новгород", 5),
        ("Челябинск", 4),
        ("Самара", 4),
        ("Уфа", 4),
        ("Ростов-на-Дону", 4),
        ("Красноярск", 3),
        ("Пермь", 3),
        ("Воронеж", 3),
        ("Волгоград", 3),
        ("Краснодар", 3),
        ("Омск", 2),
        ("Тюмень", 2),
        ("Иркутск", 2),
        ("Томск", 2),
        ("Ярославль", 2),
        ("Тула", 1),
        ("Рязань", 1),
        ("Тверь", 1),
        ("Калининград", 1),
    ],
    "en_US": [
        ("New York", 18),
        ("Los Angeles", 13),
        ("Chicago", 8),
        ("Houston", 7),
        ("Phoenix", 6),
        ("Philadelphia", 5),
        ("San Antonio", 4),
        ("San Diego", 4),
        ("Dallas", 4),
        ("San Jose", 3),
        ("Austin", 3),
        ("Jacksonville", 3),
        ("Fort Worth", 3),
        ("Columbus", 3),
        ("Charlotte", 3),
        ("Indianapolis", 2),
        ("Seattle", 2),
        ("Denver", 2),
        ("Boston", 2),
        ("Nashville", 2),
        ("Portland", 1),
        ("Detroit", 1),
        ("Baltimore", 1),
        ("Milwaukee", 1),
    ],
}
FALLBACK_OPERATORS = {
    "ru_RU": ["Алексей Смирнов", "Мария Иванова", "Ирина Петрова", "Денис Кузнецов", "Ольга Соколова"],
    "en_US": ["Alice Johnson", "Brian Smith", "Emma Davis", "Olivia Brown", "Daniel Wilson"],
}
CITY_STREETS = {
    "ru_RU": [
        "Лесная",
        "Садовая",
        "Молодежная",
        "Центральная",
        "Парковая",
        "Набережная",
        "Школьная",
        "Солнечная",
        "Заречная",
        "Полевая",
        "Советская",
        "Озерная",
        "Вокзальная",
        "Спортивная",
        "Березовая",
        "Тихая",
        "Юбилейная",
        "Гагарина",
        "Победы",
        "Мира",
        "Строителей",
        "Космонавтов",
        "Дружбы",
        "Ключевая",
        "Рябиновая",
        "Северная",
        "Южная",
        "Вишневая",
        "Луговая",
        "Зеленая",
        "Кленовая",
        "Театральная",
        "Речная",
        "Рабочая",
        "Пионерская",
        "Дачная",
        "Первомайская",
        "Восточная",
        "Западная",
        "Транспортная",
    ],
    "en_US": [
        "Oak",
        "Maple",
        "Pine",
        "Cedar",
        "Lake",
        "River",
        "Washington",
        "Lincoln",
        "Park",
        "Sunset",
        "Hillcrest",
        "Meadow",
        "Willow",
        "Madison",
        "Jefferson",
        "Highland",
        "Forest",
        "Cherry",
        "Walnut",
        "Adams",
        "Monroe",
        "Jackson",
        "Franklin",
        "Spruce",
        "Dogwood",
        "Magnolia",
        "College",
        "Market",
        "Main",
        "Church",
        "Elm",
        "Sycamore",
        "Briar",
        "Brookside",
        "Fairview",
        "Ridge",
        "Valley",
        "Laurel",
        "Heritage",
        "Kingston",
    ],
}
STREET_TYPES = {
    "ru_RU": ["ул.", "пр-т", "пер.", "бул.", "наб.", "ш."],
    "en_US": ["St", "Ave", "Blvd", "Rd", "Ln", "Dr"],
}
CITY_DISTRICTS = {
    "ru_RU": [
        "Центральный",
        "Ленинский",
        "Октябрьский",
        "Советский",
        "Северный",
        "Южный",
        "Приморский",
        "Железнодорожный",
        "Индустриальный",
        "Академический",
        "Нагорный",
        "Заречный",
    ],
    "en_US": [
        "Downtown",
        "Midtown",
        "Uptown",
        "West End",
        "East Side",
        "North Park",
        "South Ridge",
        "Old Town",
        "Riverfront",
        "University District",
        "Hill District",
        "Lakeside",
    ],
}


def apply_generation_semantics(
    tables: dict[str, list[dict[str, object]]],
    *,
    locale: str,
) -> dict[str, list[dict[str, object]]]:
    seeded_random = Random(f"generation::{locale}::{sum(len(rows) for rows in tables.values())}")

    users = tables.get("users", [])
    products = tables.get("products", [])
    orders = tables.get("orders", [])
    payments = tables.get("payments", [])
    support_tickets = tables.get("support_tickets", [])

    _adjust_users(users, locale=locale, seeded_random=seeded_random)
    _adjust_products(products, locale=locale, seeded_random=seeded_random)
    _adjust_orders(orders, users=users, locale=locale, seeded_random=seeded_random)
    _adjust_payments(payments, seeded_random=seeded_random)
    _adjust_support_tickets(
        support_tickets,
        users=users,
        locale=locale,
        seeded_random=seeded_random,
    )

    return tables


def _adjust_users(users: list[dict[str, object]], *, locale: str, seeded_random: Random) -> None:
    if not users or not _has_columns(users, {"user_id", "city", "registration_date", "birth_date"}):
        return

    city_profiles = CITY_PROFILES.get(locale, CITY_PROFILES["en_US"])
    for row in users:
        registration_date = _sample_recent_datetime(seeded_random)
        birth_date = _sample_birth_before_registration(seeded_random, registration_date)
        row["city"] = _weighted_choice(seeded_random, city_profiles)

        row["registration_date"] = registration_date.isoformat()
        row["birth_date"] = birth_date.isoformat()
        if "address" in row:
            row["address"] = _build_address_for_city(str(row["city"]), locale=locale, seeded_random=seeded_random)


def _adjust_products(products: list[dict[str, object]], *, locale: str, seeded_random: Random) -> None:
    if not products or not _has_columns(products, {"product_id", "price"}):
        return

    for row in products:
        row["price"] = _sample_product_price(seeded_random, locale=locale)


def _adjust_orders(
    orders: list[dict[str, object]],
    *,
    users: list[dict[str, object]],
    locale: str,
    seeded_random: Random,
) -> None:
    if not orders or not _has_columns(orders, {"user_id", "order_date", "amount", "currency"}):
        return

    registration_by_user_id = {
        int(row["user_id"]): _parse_datetime(str(row["registration_date"]))
        for row in users
        if row.get("user_id") is not None and row.get("registration_date")
    }
    currency_weights = [("USD", 0.72), ("RUB", 0.28)] if locale == "en_US" else [("RUB", 0.75), ("USD", 0.25)]

    for row in orders:
        user_id = int(row["user_id"])
        registration_date = registration_by_user_id.get(user_id, _sample_recent_datetime(seeded_random))
        row["order_date"] = _sample_after_datetime(
            seeded_random,
            min_date=registration_date,
            max_date=_utc_now(),
        ).isoformat()
        row["amount"] = _sample_order_quantity(seeded_random)
        row["currency"] = _weighted_choice(seeded_random, currency_weights)


def _adjust_payments(payments: list[dict[str, object]], *, seeded_random: Random) -> None:
    if not payments or not _has_columns(payments, {"payment_id", "order_id", "user_id", "status"}):
        return

    status_weights = [("success", 0.88), ("pending", 0.08), ("failed", 0.04)]
    for row in payments:
        row["status"] = _weighted_choice(seeded_random, status_weights)


def _adjust_support_tickets(
    tickets: list[dict[str, object]],
    *,
    users: list[dict[str, object]],
    locale: str,
    seeded_random: Random,
) -> None:
    if not tickets or not _has_columns(tickets, {"ticket_id", "user_id", "created_at", "status", "priority", "operator_name"}):
        return

    registration_by_user_id = {
        int(row["user_id"]): _parse_datetime(str(row["registration_date"]))
        for row in users
        if row.get("user_id") is not None and row.get("registration_date")
    }
    operator_pool = _build_operator_pool(tickets, locale=locale, size=min(10, max(1, len(tickets) // 20 + 1)))
    status_weights = [("resolved", 0.28), ("closed", 0.24), ("new", 0.24), ("in progress", 0.24)]
    priority_weights = [("low", 0.44), ("medium", 0.41), ("high", 0.15)]

    for index, row in enumerate(tickets):
        user_id = int(row["user_id"])
        registration_date = registration_by_user_id.get(user_id, _sample_recent_datetime(seeded_random))
        row["created_at"] = _sample_after_datetime(
            seeded_random,
            min_date=registration_date,
            max_date=_utc_now(),
        ).isoformat()
        row["status"] = _weighted_choice(seeded_random, status_weights)
        row["priority"] = _weighted_choice(seeded_random, priority_weights)
        row["operator_name"] = operator_pool[index % len(operator_pool)]


def _build_operator_pool(tickets: list[dict[str, object]], *, locale: str, size: int) -> list[str]:
    seen: list[str] = []
    for row in tickets:
        value = str(row.get("operator_name", "")).strip()
        if value and value not in seen:
            seen.append(value)
        if len(seen) >= size:
            return seen

    fallback = FALLBACK_OPERATORS.get(locale, FALLBACK_OPERATORS["en_US"])
    for value in fallback:
        if value not in seen:
            seen.append(value)
        if len(seen) >= size:
            break
    return seen or fallback[:1]


def _sample_recent_datetime(seeded_random: Random) -> datetime:
    now = _utc_now()
    start = now - timedelta(days=365 * 15)
    span_days = max(1, (now - start).days)
    chosen_day = seeded_random.randint(0, span_days)
    chosen_hour = seeded_random.randint(0, 23)
    chosen_minute = seeded_random.randint(0, 59)
    return start + timedelta(days=chosen_day, hours=chosen_hour, minutes=chosen_minute)


def _sample_birth_before_registration(seeded_random: Random, registration_date: datetime) -> date:
    age_band = _weighted_choice(
        seeded_random,
        [
            ((18, 24), 0.2),
            ((25, 34), 0.38),
            ((35, 44), 0.245),
            ((45, 54), 0.115),
            ((55, 64), 0.05),
            ((65, 72), 0.01),
        ],
    )
    age = seeded_random.randint(*age_band)
    max_birth = registration_date.date() - timedelta(days=365 * age)
    min_birth = max_birth - timedelta(days=364)
    span_days = max(1, (max_birth - min_birth).days)
    return min_birth + timedelta(days=seeded_random.randint(0, span_days))


def _sample_after_datetime(seeded_random: Random, *, min_date: datetime, max_date: datetime) -> datetime:
    if min_date >= max_date:
        return min_date
    span_seconds = int((max_date - min_date).total_seconds())
    return min_date + timedelta(seconds=seeded_random.randint(0, max(1, span_seconds)))


def _sample_order_quantity(seeded_random: Random) -> int:
    return int(_weighted_choice(
        seeded_random,
        [(1, 0.56), (2, 0.2), (3, 0.1), (4, 0.06), (5, 0.04), (6, 0.02), (10, 0.015), (20, 0.005)],
    ))


def _sample_product_price(seeded_random: Random, *, locale: str) -> int:
    if locale == "en_US":
        band = _weighted_choice(seeded_random, [("low", 0.45), ("mid", 0.35), ("upper", 0.15), ("premium", 0.05)])
        ranges = {
            "low": (5, 25),
            "mid": (25, 120),
            "upper": (120, 350),
            "premium": (350, 900),
        }
    else:
        band = _weighted_choice(seeded_random, [("low", 0.4), ("mid", 0.35), ("upper", 0.2), ("premium", 0.05)])
        ranges = {
            "low": (99, 990),
            "mid": (1000, 5000),
            "upper": (5000, 15000),
            "premium": (15000, 50000),
        }

    min_value, max_value = ranges[band]
    return seeded_random.randint(min_value, max_value)


def _build_address_for_city(city: str, *, locale: str, seeded_random: Random) -> str:
    streets = CITY_STREETS.get(locale, CITY_STREETS["en_US"])
    street_types = STREET_TYPES.get(locale, STREET_TYPES["en_US"])
    districts = CITY_DISTRICTS.get(locale, CITY_DISTRICTS["en_US"])
    street_name = seeded_random.choice(streets)
    street_type = seeded_random.choice(street_types)
    house = seeded_random.randint(1, 220)

    if locale == "ru_RU":
        district = seeded_random.choice(districts)
        building = f", корп. {seeded_random.randint(1, 8)}" if seeded_random.random() < 0.18 else ""
        apartment = f", кв. {seeded_random.randint(1, 400)}" if seeded_random.random() < 0.72 else ""
        patterns = [
            f"г. {city}, {street_type} {street_name}, д. {house}{building}{apartment}",
            f"г. {city}, {district} район, {street_type} {street_name}, д. {house}{building}{apartment}",
            f"{city}, {street_type} {street_name}, влад. {house}{building}{apartment}",
        ]
        return seeded_random.choice(patterns)

    district = seeded_random.choice(districts)
    suite = f", Apt {seeded_random.randint(1, 999)}" if seeded_random.random() < 0.55 else ""
    patterns = [
        f"{house} {street_name} {street_type}, {city}{suite}",
        f"{house} {street_name} {street_type}, {district}, {city}{suite}",
        f"{house} {street_name} {street_type}, Unit {seeded_random.randint(1, 80)}, {city}",
    ]
    return seeded_random.choice(patterns)


def _weighted_choice(seeded_random: Random, weighted_items: list[tuple[Any, float]]) -> Any:
    total_weight = sum(weight for _, weight in weighted_items)
    if total_weight <= 0:
        raise ValueError("Список weighted_items должен содержать положительную сумму весов.")

    threshold = seeded_random.random() * total_weight
    total = 0.0
    for value, weight in weighted_items:
        total += weight
        if threshold < total:
            return value
    return weighted_items[-1][0]


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _has_columns(rows: list[dict[str, object]], required_columns: set[str]) -> bool:
    first_row = rows[0] if rows else {}
    return required_columns.issubset(first_row.keys())
