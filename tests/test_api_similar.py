import base64
import csv
import io

from fastapi.testclient import TestClient

from sda.web.app import app

client = TestClient(app)


def _build_orders_csv() -> bytes:
    return (
        "order_id,amount,status,created_at\n"
        "1,10.5,new,2024-01-01\n"
        "2,20.0,paid,2024-01-02\n"
        "3,15.2,paid,2024-01-03\n"
        "4,18.1,cancelled,2024-01-04\n"
        "5,30.0,new,2024-01-05\n"
        "6,22.4,paid,2024-01-06\n"
    ).encode("utf-8")


def test_post_similar_analyze_returns_profiles_and_preview() -> None:
    response = client.post(
        "/api/v1/similar/analyze",
        files={"file": ("orders.csv", _build_orders_csv(), "text/csv")},
        data={"has_header": "true", "preview_rows_limit": "3"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"].startswith("ana_")
    assert payload["file_name"] == "orders.csv"
    assert payload["row_count"] == 6
    assert payload["column_count"] == 4
    assert len(payload["preview_rows"]) == 3

    columns = {item["name"]: item for item in payload["columns"]}
    assert columns["amount"]["inferred_type"] == "numerical"
    assert columns["created_at"]["inferred_type"] == "datetime"


def test_post_similar_run_returns_generated_csv() -> None:
    analyze_response = client.post(
        "/api/v1/similar/analyze",
        files={"file": ("orders.csv", _build_orders_csv(), "text/csv")},
        data={"has_header": "true"},
    )
    analyze_payload = analyze_response.json()

    run_response = client.post(
        "/api/v1/similar/run",
        json={
            "analysis_id": analyze_payload["analysis_id"],
            "target_rows": 4,
        },
    )

    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["analysis_id"] == analyze_payload["analysis_id"]
    assert payload["file_name"] == "orders_similar.csv"
    assert payload["row_count"] == 4
    assert payload["column_count"] == 4
    assert payload["result_format"] == "csv_base64"

    decoded = base64.b64decode(payload["content_base64"]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(decoded)))
    assert len(rows) == 4
    assert set(rows[0]) == {"order_id", "amount", "status", "created_at"}
    assert [row["order_id"] for row in rows] == ["1", "2", "3", "4"]
    assert rows[0]["created_at"]


def test_post_similar_analyze_rejects_non_csv() -> None:
    response = client.post(
        "/api/v1/similar/analyze",
        files={"file": ("notes.txt", b"hello", "text/plain;charset=utf-8")},
        data={"has_header": "true"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "invalid_file_type"


def test_post_similar_run_returns_analysis_not_found() -> None:
    response = client.post(
        "/api/v1/similar/run",
        json={
            "analysis_id": "ana_999999",
            "target_rows": 3,
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error_code"] == "analysis_not_found"
