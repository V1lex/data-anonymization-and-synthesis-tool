import base64
import csv
import io
import zipfile

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


def test_post_similar_multi_analyze_and_run_returns_zip() -> None:
    users_csv = (
        "user_id,name\n"
        "1,Alice\n"
        "2,Bob\n"
        "3,Carol\n"
        "4,Dan\n"
        "5,Eve\n"
        "6,Fay\n"
    ).encode("utf-8")
    orders_csv = (
        "order_id,user_id,amount\n"
        "1,1,10\n"
        "2,2,20\n"
        "3,1,15\n"
        "4,3,30\n"
        "5,4,25\n"
        "6,5,40\n"
    ).encode("utf-8")

    analyze_response = client.post(
        "/api/v1/similar/multi/analyze",
        files=[
            ("files", ("users.csv", users_csv, "text/csv")),
            ("files", ("orders.csv", orders_csv, "text/csv")),
        ],
        data={"has_header": "true", "preview_rows_limit": "2"},
    )

    assert analyze_response.status_code == 200
    analyze_payload = analyze_response.json()
    assert analyze_payload["analysis_id"].startswith("mta_")
    assert analyze_payload["table_count"] == 2
    assert [table["table_name"] for table in analyze_payload["tables"]] == ["users", "orders"]
    assert analyze_payload["relationships"] == [
        {
            "parent_table_name": "users",
            "child_table_name": "orders",
            "parent_primary_key": "user_id",
            "child_foreign_key": "user_id",
        }
    ]

    run_response = client.post(
        "/api/v1/similar/multi/run",
        json={"analysis_id": analyze_payload["analysis_id"], "scale": 1.0},
    )

    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["result_format"] == "zip_base64"
    assert run_payload["file_name"] == "similar_dataset.zip"
    archive = zipfile.ZipFile(io.BytesIO(base64.b64decode(run_payload["archive_base64"])))
    assert archive.namelist() == ["users_similar.csv", "orders_similar.csv"]


def test_post_similar_multi_analyze_requires_two_files() -> None:
    response = client.post(
        "/api/v1/similar/multi/analyze",
        files=[("files", ("users.csv", b"user_id,name\n1,Alice\n", "text/csv"))],
        data={"has_header": "true"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "validation_error"
