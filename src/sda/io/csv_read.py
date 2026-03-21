from __future__ import annotations

import csv
import io
from typing import Any, BinaryIO, TextIO

from sda.core.domain.errors import CsvEmptyError, CsvInvalidHeaderError, CsvMalformedError

SUPPORTED_DELIMITERS = (",", ";")


def detect_delimiter(text: str, default: str = ",") -> str:
    """Detect delimiter using the first non-empty line."""
    for line in text.splitlines():
        if line.strip():
            comma_count = line.count(",")
            semicolon_count = line.count(";")
            if semicolon_count > comma_count:
                return ";"
            if comma_count > 0:
                return ","
            return default
    return default


def _read_file_like(source: Any, encoding: str = "utf-8") -> str:
    """Read bytes/text/file-like into unicode text."""
    if hasattr(source, "seek"):
        source.seek(0)

    if isinstance(source, str):
        return source

    if isinstance(source, bytes):
        return source.decode(encoding)

    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, bytes):
            return raw.decode(encoding)
        return str(raw)

    raise TypeError("source must be bytes, str or file-like object")


def read_csv(
    source: bytes | str | BinaryIO | TextIO,
    delimiter: str | None = None,
    encoding: str = "utf-8",
) -> tuple[list[dict[str, str]], list[str], str]:
    """
    Read CSV from upload/file-like object.

    Returns:
        (rows, header, used_delimiter)
    """
    text = _read_file_like(source, encoding=encoding)
    if not text or not text.strip():
        raise CsvEmptyError("CSV is empty")

    used_delimiter = delimiter or detect_delimiter(text)
    if used_delimiter not in SUPPORTED_DELIMITERS:
        raise CsvMalformedError("Unsupported delimiter")

    reader = csv.reader(io.StringIO(text), delimiter=used_delimiter)
    try:
        parsed_rows = list(reader)
    except csv.Error as exc:
        raise CsvMalformedError(f"Malformed CSV: {exc}") from exc

    if not parsed_rows:
        raise CsvEmptyError("CSV is empty")

    header = [col.strip() for col in parsed_rows[0]]
    if not header or any(not col for col in header):
        raise CsvInvalidHeaderError("CSV header contains empty column names")
    if len(set(header)) != len(header):
        raise CsvInvalidHeaderError("CSV header contains duplicate columns")

    data_rows = parsed_rows[1:]
    result: list[dict[str, str]] = []
    for row in data_rows:
        if len(row) != len(header):
            raise CsvMalformedError("CSV row length does not match header")
        result.append({header[idx]: value for idx, value in enumerate(row)})

    return result, header, used_delimiter
