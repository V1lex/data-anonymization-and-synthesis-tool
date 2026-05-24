import csv
import io
from collections import Counter
from datetime import datetime

from sda.core.similar.postprocess import postprocess_similar_rows
from sda.use_cases.generate_csv import generate_csv_use_case


def _decode_generated_rows(result: dict, template_id: str) -> list[dict[str, str]]:
    item = next(file for file in result["generated_files"] if file["template_id"] == template_id)
    return list(csv.DictReader(io.StringIO(item["content"].decode("utf-8"))))


def test_generate_semantics_keep_order_dates_after_registration_and_ticket_constraints() -> None:
    result = generate_csv_use_case(
        [
            {"template_id": "users", "row_count": 120},
            {"template_id": "products", "row_count": 40},
            {"template_id": "orders", "row_count": 180},
            {"template_id": "payments", "row_count": 180},
            {"template_id": "support_tickets", "row_count": 150},
        ],
        locale="ru_RU",
    )

    users = _decode_generated_rows(result, "users")
    orders = _decode_generated_rows(result, "orders")
    payments = _decode_generated_rows(result, "payments")
    tickets = _decode_generated_rows(result, "support_tickets")

    registration_by_user = {
        row["user_id"]: datetime.fromisoformat(row["registration_date"])
        for row in users
    }

    assert sum(1 for row in payments if row["status"] == "success") > sum(1 for row in payments if row["status"] == "failed")
    assert len({row["operator_name"] for row in tickets}) <= 10

    for row in orders:
        assert datetime.fromisoformat(row["order_date"]) >= registration_by_user[row["user_id"]]

    for row in tickets:
        assert datetime.fromisoformat(row["created_at"]) >= registration_by_user[row["user_id"]]


def test_generate_semantics_keep_city_separate_from_address_and_reduce_very_old_birth_dates() -> None:
    result = generate_csv_use_case(
        [
            {"template_id": "users", "row_count": 400},
        ],
        locale="ru_RU",
    )

    users = _decode_generated_rows(result, "users")

    for row in users:
        assert row["address"]
        assert row["city"] not in row["address"]

    city_counts = Counter(row["city"] for row in users)
    assert len(city_counts) >= 12
    assert city_counts["Москва"] > city_counts["Тула"]

    births_in_1940s = sum(1 for row in users if datetime.fromisoformat(row["birth_date"]).year < 1950)
    assert births_in_1940s <= 8
