import base64

import pytest

from sda.core.domain.errors import InvalidRuleError
from sda.use_cases.anonymize_csv import prepare_anonymize_upload, run_anonymize_use_case


def test_prepare_anonymize_upload_builds_preview_and_suggestions() -> None:
    csv_bytes = (
        "full_name,email,birth_date\n"
        "Alice Example,alice@example.com,1991-04-08\n"
        "Bob Example,bob@example.com,1987-11-02\n"
    ).encode("utf-8")

    result = prepare_anonymize_upload(
        file_name="people.csv",
        content=csv_bytes,
        suggest=True,
    )

    assert result["row_count"] == 2
    assert result["column_count"] == 3
    assert result["delimiter"] == ","
    assert result["preview_rows"][0]["full_name"] == "Alice Example"
    assert [column["name"] for column in result["columns"]] == ["full_name", "email", "birth_date"]
    assert result["columns"][1]["suggested_method"] == "mask"
    assert result["columns"][2]["suggested_method"] == "generalize_year"


def test_run_anonymize_use_case_applies_rules_and_returns_csv_base64() -> None:
    rows = [
        {
            "full_name": "Alice Example",
            "email": "alice@example.com",
            "birth_date": "1991-04-08",
            "city": "Moscow",
        }
    ]

    result = run_anonymize_use_case(
        upload_id="upl_test123",
        file_name="people.csv",
        rows=rows,
        header=["full_name", "email", "birth_date", "city"],
        delimiter=",",
        rules=[
            {"column_name": "full_name", "method": "pseudonymize", "params": {}},
            {"column_name": "email", "method": "mask", "params": {"keep_domain": True}},
            {"column_name": "birth_date", "method": "generalize_year", "params": {}},
            {"column_name": "city", "method": "redact", "params": {}},
        ],
    )

    decoded = base64.b64decode(result["content_base64"]).decode("utf-8")

    assert result["result_format"] == "csv_base64"
    assert result["file_name"] == "people_anonymized.csv"
    assert "pseudo_" in decoded
    assert "a***@example.com" in decoded
    assert "1991" in decoded
    assert "[REDACTED]" in decoded


def test_run_anonymize_use_case_rejects_invalid_generalize_year_rule() -> None:
    with pytest.raises(InvalidRuleError):
        run_anonymize_use_case(
            upload_id="upl_test123",
            file_name="people.csv",
            rows=[{"city": "Moscow"}],
            header=["city"],
            delimiter=",",
            rules=[{"column_name": "city", "method": "generalize_year", "params": {}}],
        )
