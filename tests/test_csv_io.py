from io import BytesIO

import pytest

from sda.core.domain.errors import CsvEmptyError, CsvInvalidHeaderError, CsvMalformedError
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
