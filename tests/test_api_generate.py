import base64
import csv
import io

from fastapi.testclient import TestClient

from sda.web.app import app

client = TestClient(app)


def test_get_generate_templates_returns_catalog() -> None:
    response = client.get("/api/v1/generate/templates")

    assert response.status_code == 200
    payload = response.json()
    assert [item["template_id"] for item in payload["items"]] == [
        "users",
        "orders",
        "payments",
        "products",
        "support_tickets",
    ]
    users_item = next(item for item in payload["items"] if item["template_id"] == "users")
    assert users_item["preview_columns"] == [
        "user_id",
        "full_name",
        "email",
        "phone",
        "city",
        "address",
        "birth_date",
        "registration_date",
    ]
    orders_item = next(item for item in payload["items"] if item["template_id"] == "orders")
    assert orders_item["preview_columns"] == [
        "order_id",
        "user_id",
        "product_id",
        "amount",
        "order_date",
        "currency",
    ]


def test_get_generate_domains_returns_sprint_four_categories() -> None:
    response = client.get("/api/v1/generate/domains")

    assert response.status_code == 200
    payload = response.json()
    assert [item["domain_id"] for item in payload["items"]] == [
        "ecommerce",
        "fintech",
        "shops",
        "logistics",
        "education",
        "crm",
    ]


def test_post_generate_run_returns_csv_base64_for_single_template() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={"items": [{"template_id": "users", "row_count": 2}], "locale": "en_US"},
    )

    assert response.status_code == 200
    payload = response.json()
    decoded = base64.b64decode(payload["content_base64"]).decode("utf-8")

    assert payload["result_format"] == "csv_base64"
    assert payload["file_name"] == "users.csv"
    assert payload["total_rows"] == 2
    assert payload["archive_base64"] is None
    assert decoded.startswith("user_id,full_name,email,phone,city,address,birth_date,registration_date\n")
    rows = list(csv.DictReader(io.StringIO(decoded)))
    assert [row["user_id"] for row in rows] == ["1", "2"]


def test_post_generate_run_applies_selected_domain_to_products() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={
            "items": [{"template_id": "products", "row_count": 3}],
            "locale": "en_US",
            "domain": "logistics",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    decoded = base64.b64decode(payload["content_base64"]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(decoded)))
    logistics_names = {
        "Warehouse delivery",
        "Express shipment",
        "Pallet slot",
        "Cold-chain transport",
        "Courier route",
        "Cargo insurance",
    }

    assert {row["name"].rsplit(" ", 1)[0] for row in rows}.issubset(logistics_names)


def test_post_generate_run_applies_education_domain_to_products() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={
            "items": [{"template_id": "products", "row_count": 4}],
            "locale": "ru_RU",
            "domain": "education",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    decoded = base64.b64decode(payload["content_base64"]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(decoded)))

    education_markers = ("курс", "интенсив", "модуль", "сессия", "тренажёр")
    assert all(
        any(marker in row["name"].lower() for marker in education_markers)
        for row in rows
    )


def test_post_generate_run_builds_plausible_ru_addresses() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={"items": [{"template_id": "users", "row_count": 10}], "locale": "ru_RU"},
    )

    assert response.status_code == 200
    payload = response.json()
    decoded = base64.b64decode(payload["content_base64"]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(decoded)))

    assert all(", д. " in row["address"] for row in rows)
    assert all("влад." not in row["address"] for row in rows)


def test_post_generate_run_rejects_unsupported_locale() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={"items": [{"template_id": "users", "row_count": 2}], "locale": "de_DE"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "validation_error"


def test_post_generate_run_rejects_unsupported_domain() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={
            "items": [{"template_id": "products", "row_count": 2}],
            "domain": "medicine",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "validation_error"


def test_post_generate_run_rejects_duplicate_templates() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={
            "items": [
                {"template_id": "users", "row_count": 1},
                {"template_id": "users", "row_count": 1},
            ]
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "validation_error"


def test_post_generate_run_orders_dependency_chain_before_generation() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={
            "items": [
                {"template_id": "orders", "row_count": 2},
                {"template_id": "users", "row_count": 2},
                {"template_id": "products", "row_count": 2},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result_format"] == "zip_base64"
    assert [item["template_id"] for item in payload["generated_files"]] == ["users", "products", "orders"]


def test_post_generate_run_rejects_missing_dependencies() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={"items": [{"template_id": "orders", "row_count": 1}]},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "generation_failed"
    assert payload["details"]["missing_dependencies"] == ["users", "products"]
