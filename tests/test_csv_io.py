from io import BytesIO

import pytest

from sda.core.domain.errors import (
    CsvEmptyError,
    CsvInvalidHeaderError,
    CsvMalformedError,
    GenerationError,
)
from sda.io.csv_read import detect_delimiter, read_csv
from sda.io.csv_write import write_csv


def test_detect_delimiter_comma() -> None:
    text = "id,name\n1,Alice\n"
    assert detect_delimiter(text) == ","


def test_detect_delimiter_semicolon() -> None:
    text = "id;name\n1;Alice\n"
    assert detect_delimiter(text) == ";"


def test_read_csv_from_upload_file_like() -> None:
    upload = BytesIO(b"id,name\n1,Alice\n2,Bob\n")
    rows, header, used_delimiter = read_csv(upload)

    assert used_delimiter == ","
    assert header == ["id", "name"]
    assert rows == [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]


def test_read_csv_handles_utf8_bom() -> None:
    upload = BytesIO("id,name\n1,Андрей\n".encode("utf-8-sig"))
    rows, header, used_delimiter = read_csv(upload)

    assert used_delimiter == ","
    assert header == ["id", "name"]
    assert rows == [{"id": "1", "name": "Андрей"}]


def test_read_csv_handles_bom_in_text_source() -> None:
    rows, header, used_delimiter = read_csv("\ufeffid,name\n1,Alice\n")

    assert used_delimiter == ","
    assert header == ["id", "name"]
    assert rows == [{"id": "1", "name": "Alice"}]


def test_read_csv_ignores_blank_lines() -> None:
    upload = BytesIO(b"\n\nid,name\n\n1,Alice\n   \n2,Bob\n\n")
    rows, header, used_delimiter = read_csv(upload)

    assert used_delimiter == ","
    assert header == ["id", "name"]
    assert rows == [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]


def test_read_csv_handles_semicolon_and_blank_lines() -> None:
    upload = BytesIO("id;name\n\n1;Андрей\n2;Мария\n".encode("utf-8"))
    rows, header, used_delimiter = read_csv(upload)

    assert used_delimiter == ";"
    assert header == ["id", "name"]
    assert rows == [{"id": "1", "name": "Андрей"}, {"id": "2", "name": "Мария"}]


def test_read_csv_handles_cp1251_when_default_utf8_fails() -> None:
    upload = BytesIO("id,name\n1,Андрей\n".encode("cp1251"))
    rows, header, used_delimiter = read_csv(upload)

    assert used_delimiter == ","
    assert header == ["id", "name"]
    assert rows == [{"id": "1", "name": "Андрей"}]


def test_read_csv_without_header_ignores_leading_blank_lines() -> None:
    upload = BytesIO(b"\n\n1,Alice\n2,Bob\n")
    rows, header, used_delimiter = read_csv(upload, has_header=False)

    assert used_delimiter == ","
    assert header == ["column_1", "column_2"]
    assert rows == [
        {"column_1": "1", "column_2": "Alice"},
        {"column_1": "2", "column_2": "Bob"},
    ]


def test_read_csv_raises_on_empty_csv() -> None:
    with pytest.raises(CsvEmptyError):
        read_csv(BytesIO(b""))


def test_read_csv_raises_on_broken_structure() -> None:
    broken = BytesIO(b"id,name\n1,Alice\n2\n")
    with pytest.raises(CsvMalformedError):
        read_csv(broken)


def test_read_csv_raises_on_invalid_header() -> None:
    invalid = BytesIO(b"id,,name\n1,2,Alice\n")
    with pytest.raises(CsvInvalidHeaderError):
        read_csv(invalid)


def test_read_csv_raises_on_header_only_csv() -> None:
    with pytest.raises(CsvEmptyError):
        read_csv(BytesIO(b"id,name\n"))


def test_write_csv_returns_utf8_bytes() -> None:
    rows = [{"id": "1", "name": "Андрей"}]
    data = write_csv(rows, header=["id", "name"], delimiter=",")
    decoded = data.decode("utf-8")

    assert decoded.startswith("id,name\n")
    assert "Андрей" in decoded


def test_write_csv_with_semicolon_delimiter() -> None:
    rows = [{"id": "1", "name": "Alice"}]
    data = write_csv(rows, delimiter=";")
    decoded = data.decode("utf-8")

    assert decoded == "id;name\n1;Alice\n"


def test_write_csv_supports_utf8_sig_encoding() -> None:
    rows = [{"id": "1", "name": "Андрей"}]
    data = write_csv(rows, header=["id", "name"], encoding="utf-8-sig")

    assert data.startswith(b"\xef\xbb\xbf")
    assert "Андрей" in data.decode("utf-8-sig")


def test_write_csv_wraps_encoding_errors() -> None:
    rows = [{"id": "1", "name": "Андрей"}]

    with pytest.raises(GenerationError):
        write_csv(rows, header=["id", "name"], encoding="ascii")
