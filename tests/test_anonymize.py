import base64
import csv
import io

import pytest

from sda.core.domain.errors import FileTooLargeError, InvalidRuleError, ValidationError
from sda.use_cases.anonymize_csv import prepare_anonymize_upload, run_anonymize_use_case


def test_prepare_anonymize_upload_builds_preview() -> None:
    csv_bytes = (
        "full_name,email,birth_date\n"
        "Alice Example,alice@example.com,1991-04-08\n"
        "Bob Example,bob@example.com,1987-11-02\n"
    ).encode("utf-8")

    result = prepare_anonymize_upload(
        file_name="people.csv",
        content=csv_bytes,
    )

    assert result["row_count"] == 2
    assert result["column_count"] == 3
    assert result["delimiter"] == ","
    assert result["preview_rows"][0]["full_name"] == "Alice Example"
    assert [column["name"] for column in result["columns"]] == ["full_name", "email", "birth_date"]
    assert result["columns"][0]["detected_type"] == "full_name"
    assert result["columns"][1]["suggested_method"] == "mask"
    assert result["columns"][1]["reason"]
    assert result["columns"][1]["hint"]
    birth_date_column = next(column for column in result["columns"] if column["name"] == "birth_date")
    assert "mask" in birth_date_column["unsupported_methods"]
    assert "pseudonymize" in birth_date_column["unsupported_methods"]
    assert birth_date_column["suggested_method"] == "generalize_year"


def test_prepare_anonymize_upload_auto_detects_semicolon_delimiter() -> None:
    csv_bytes = "full_name;email\nAlice Example;alice@example.com\n".encode("utf-8")

    result = prepare_anonymize_upload(
        file_name="people.csv",
        content=csv_bytes,
    )

    assert result["delimiter"] == ";"


def test_prepare_anonymize_upload_rejects_invalid_delimiter() -> None:
    csv_bytes = "full_name,email\nAlice Example,alice@example.com\n".encode("utf-8")

    with pytest.raises(ValidationError):
        prepare_anonymize_upload(
            file_name="people.csv",
            content=csv_bytes,
            delimiter="|",
        )


def test_prepare_anonymize_upload_rejects_too_many_rows() -> None:
    csv_bytes = ("email\n" + "\n".join(f"user{index}@example.com" for index in range(10_001))).encode("utf-8")

    with pytest.raises(ValidationError):
        prepare_anonymize_upload(
            file_name="people.csv",
            content=csv_bytes,
        )


def test_prepare_anonymize_upload_rejects_file_too_large() -> None:
    csv_bytes = b"email\n" + (b"a" * (5 * 1024 * 1024))

    with pytest.raises(FileTooLargeError):
        prepare_anonymize_upload(
            file_name="people.csv",
            content=csv_bytes,
        )


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
        upload_id="upload_1",
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
    record = next(csv.DictReader(io.StringIO(decoded)))

    assert result["result_format"] == "csv_base64"
    assert result["file_name"] == "people_anonymized.csv"
    assert record["full_name"] != "Alice Example"
    assert not record["full_name"].startswith("pseudo_")
    assert record["email"] == "a***@example.com"
    assert record["birth_date"] == "1991"
    assert record["city"] == "[REDACTED]"


def test_run_anonymize_use_case_masks_phone_and_text_readably() -> None:
    rows = [
        {
            "phone": "+7 901 234-56-78",
            "city": "Saint Petersburg",
        }
    ]

    result = run_anonymize_use_case(
        upload_id="upload_1",
        file_name="people.csv",
        rows=rows,
        header=["phone", "city"],
        delimiter=",",
        rules=[
            {"column_name": "phone", "method": "mask", "params": {}},
            {"column_name": "city", "method": "mask", "params": {}},
        ],
    )

    decoded = base64.b64decode(result["content_base64"]).decode("utf-8")
    record = next(csv.DictReader(io.StringIO(decoded)))

    assert record["phone"].endswith("78")
    assert "*" in record["phone"]
    assert record["city"].startswith("S")
    assert "*" in record["city"]
    assert record["city"] != "****************"


def test_prepare_anonymize_upload_marks_unsupported_methods_in_metadata() -> None:
    csv_bytes = "amount\n15\n".encode("utf-8")

    result = prepare_anonymize_upload(
        file_name="orders.csv",
        content=csv_bytes,
    )

    amount_column = result["columns"][0]
    assert amount_column["name"] == "amount"
    assert "mask" in amount_column["unsupported_methods"]
    assert "pseudonymize" in amount_column["unsupported_methods"]


def test_run_anonymize_use_case_rejects_invalid_generalize_year_rule() -> None:
    with pytest.raises(InvalidRuleError):
        run_anonymize_use_case(
            upload_id="upload_1",
            file_name="people.csv",
            rows=[{"city": "Moscow"}],
            header=["city"],
            delimiter=",",
            rules=[{"column_name": "city", "method": "generalize_year", "params": {}}],
        )


def test_run_anonymize_use_case_rejects_invalid_generalize_year_rule_anywhere_in_column() -> None:
    rows = [{"birth_date": f"199{index}-01-01"} for index in range(5)] + [{"birth_date": "Moscow"}]

    with pytest.raises(InvalidRuleError):
        run_anonymize_use_case(
            upload_id="upload_1",
            file_name="people.csv",
            rows=rows,
            header=["birth_date"],
            delimiter=",",
            rules=[{"column_name": "birth_date", "method": "generalize_year", "params": {}}],
        )


def test_run_anonymize_use_case_rejects_mask_for_numeric_amount() -> None:
    with pytest.raises(InvalidRuleError, match="числовой колонки 'amount'"):
        run_anonymize_use_case(
            upload_id="upload_1",
            file_name="orders.csv",
            rows=[{"amount": "15"}],
            header=["amount"],
            delimiter=",",
            rules=[{"column_name": "amount", "method": "mask", "params": {}}],
        )


def test_run_anonymize_use_case_rejects_pseudonymize_for_dates() -> None:
    with pytest.raises(InvalidRuleError, match="для дат используйте 'Обобщение до года'"):
        run_anonymize_use_case(
            upload_id="upload_1",
            file_name="people.csv",
            rows=[{"birth_date": "1991-04-08"}],
            header=["birth_date"],
            delimiter=",",
            rules=[{"column_name": "birth_date", "method": "pseudonymize", "params": {}}],
        )
