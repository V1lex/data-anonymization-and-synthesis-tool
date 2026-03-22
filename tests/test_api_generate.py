import base64

from fastapi.testclient import TestClient

from sda.web.app import app

client = TestClient(app)


def test_get_generate_templates_returns_catalog() -> None:
    response = client.get("/api/v1/generate/templates")

    assert response.status_code == 200
    payload = response.json()
    template_ids = {item["template_id"] for item in payload["items"]}
    assert {"users", "orders", "payments", "products", "support_tickets"} <= template_ids


def test_post_generate_run_returns_csv_base64_for_single_template() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={"items": [{"template_id": "users", "row_count": 2}]},
    )

    assert response.status_code == 200
    payload = response.json()
    decoded = base64.b64decode(payload["content_base64"]).decode("utf-8")

    assert payload["result_format"] == "csv_base64"
    assert payload["file_name"] == "users.csv"
    assert payload["total_rows"] == 2
    assert payload["archive_base64"] is None
    assert decoded.startswith("user_id,full_name,email,phone,city,address,birth_date,registration_date\n")


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
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result_format"] == "zip_base64"
    assert [item["template_id"] for item in payload["generated_files"]] == ["users", "orders"]


def test_post_generate_run_rejects_missing_dependencies() -> None:
    response = client.post(
        "/api/v1/generate/run",
        json={"items": [{"template_id": "orders", "row_count": 1}]},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "generation_failed"
    assert payload["details"]["missing_dependencies"] == ["users"]
