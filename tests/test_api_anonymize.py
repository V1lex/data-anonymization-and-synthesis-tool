import base64

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
        data={"delimiter": ",", "has_header": "true", "suggest": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "people.csv"
    assert payload["row_count"] == 2
    assert payload["column_count"] == 3
    assert payload["columns"][1]["name"] == "email"
    assert payload["preview_rows"][0]["full_name"] == "Alice Example"


def test_post_anonymize_run_returns_anonymized_csv() -> None:
    csv_bytes = (
        "full_name,email,birth_date,city\n"
        "Alice Example,alice@example.com,1991-04-08,Moscow\n"
    ).encode("utf-8")

    upload_response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("people.csv", csv_bytes, "text/csv")},
        data={"delimiter": ",", "has_header": "true", "suggest": "true"},
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

    assert payload["result_format"] == "csv_base64"
    assert payload["file_name"] == "people_anonymized.csv"
    assert "pseudo_" in decoded
    assert "a***@example.com" in decoded
    assert "1991" in decoded
    assert "[REDACTED]" in decoded


def test_post_anonymize_upload_rejects_non_csv_file() -> None:
    response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("notes.txt", b"hello", "text/plain;charset=utf-8")},
        data={"delimiter": ",", "has_header": "true", "suggest": "true"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "invalid_file_type"


def test_post_anonymize_upload_rejects_header_only_csv() -> None:
    response = client.post(
        "/api/v1/anonymize/upload",
        files={"file": ("people.csv", b"full_name,email\n", "text/csv")},
        data={"delimiter": ",", "has_header": "true", "suggest": "true"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "empty_file"
