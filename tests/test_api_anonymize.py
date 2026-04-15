import base64
import csv
import io

from fastapi.testclient import TestClient

from sda.web.app import app

client = TestClient(app)


def test_post_anonymize_upload_returns_columns_and_preview() -> None:
    csv_bytes = (
        "full_name,email,birth_date\n"
        "Alice Example,alice@example.com,1991-04-08\n"
        "Bob Example,bob@example.com,1987-11-02\n"
    ).encode("utf-8")

    response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("people.csv", csv_bytes, "text/csv")},
        data={"delimiter": ",", "has_header": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "people.csv"
    assert payload["row_count"] == 2
    assert payload["column_count"] == 3
    assert payload["columns"][1]["name"] == "email"
    assert payload["columns"][1]["detected_type"] == "email"
    assert payload["columns"][1]["suggested_method"] == "mask"
    assert payload["columns"][1]["reason"]
    assert payload["columns"][1]["hint"]
    assert "mask" in payload["columns"][2]["unsupported_methods"]
    assert payload["preview_rows"][0]["full_name"] == "Alice Example"


def test_post_anonymize_run_returns_anonymized_csv() -> None:
    csv_bytes = (
        "full_name,email,birth_date,city\n"
        "Alice Example,alice@example.com,1991-04-08,Moscow\n"
    ).encode("utf-8")

    upload_response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("people.csv", csv_bytes, "text/csv")},
        data={"delimiter": ",", "has_header": "true"},
    )
    upload_payload = upload_response.json()

    run_response = client.post(
        "/api/v1/anonymize/run",
        json={
            "upload_id": upload_payload["upload_id"],
            "rules": [
                {"column_name": "full_name", "method": "pseudonymize", "params": {}},
                {"column_name": "email", "method": "mask", "params": {"keep_domain": True}},
                {"column_name": "birth_date", "method": "generalize_year", "params": {}},
                {"column_name": "city", "method": "redact", "params": {}},
            ],
        },
    )

    assert run_response.status_code == 200
    payload = run_response.json()
    decoded = base64.b64decode(payload["content_base64"]).decode("utf-8")
    record = next(csv.DictReader(io.StringIO(decoded)))

    assert payload["result_format"] == "csv_base64"
    assert payload["file_name"] == "people_anonymized.csv"
    assert record["full_name"] != "Alice Example"
    assert not record["full_name"].startswith("pseudo_")
    assert record["email"] == "a***@example.com"
    assert record["birth_date"] == "1991"
    assert record["city"] == "[REDACTED]"


def test_post_anonymize_upload_rejects_non_csv_file() -> None:
    response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("notes.txt", b"hello", "text/plain;charset=utf-8")},
        data={"delimiter": ",", "has_header": "true"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "invalid_file_type"


def test_post_anonymize_upload_rejects_header_only_csv() -> None:
    response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("people.csv", b"full_name,email\n", "text/csv")},
        data={"delimiter": ",", "has_header": "true"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "empty_file"


def test_post_anonymize_upload_detects_semicolon_delimiter() -> None:
    csv_bytes = "full_name;email\nAlice Example;alice@example.com\n".encode("utf-8")

    response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("people.csv", csv_bytes, "text/csv")},
        data={"has_header": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["delimiter"] == ";"


def test_post_anonymize_upload_rejects_invalid_delimiter() -> None:
    csv_bytes = "full_name,email\nAlice Example,alice@example.com\n".encode("utf-8")

    response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("people.csv", csv_bytes, "text/csv")},
        data={"delimiter": "|", "has_header": "true"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "validation_error"


def test_post_anonymize_run_returns_detailed_invalid_rule_message() -> None:
    csv_bytes = "amount\n15\n".encode("utf-8")

    upload_response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("orders.csv", csv_bytes, "text/csv")},
        data={"delimiter": ",", "has_header": "true"},
    )
    upload_payload = upload_response.json()

    run_response = client.post(
        "/api/v1/anonymize/run",
        json={
            "upload_id": upload_payload["upload_id"],
            "rules": [
                {"column_name": "amount", "method": "mask", "params": {}},
            ],
        },
    )

    assert run_response.status_code == 400
    payload = run_response.json()
    assert payload["error_code"] == "invalid_rule"
    assert "числовой колонки 'amount'" in payload["message"]
