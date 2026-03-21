import csv
import io
from typing import Any, BinaryIO, TextIO

from sda.core.domain.errors import CsvEmptyError, CsvInvalidHeaderError, CsvMalformedError

SUPPORTED_DELIMITERS = (",", ";")


def detect_delimiter(text: str, default: str = ",") -> str:
    """Определить разделитель по первой непустой строке."""
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
    """Прочитать bytes/str/file-like и вернуть unicode-строку."""
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

    raise TypeError("source должен быть bytes, str или file-like объектом")


def read_csv(
    source: bytes | str | BinaryIO | TextIO,
    delimiter: str | None = None,
    encoding: str = "utf-8",
) -> tuple[list[dict[str, str]], list[str], str]:
    """Прочитать CSV из upload/file-like объекта.

    Возвращает кортеж: (rows, header, used_delimiter).
    """
    text = _read_file_like(source, encoding=encoding)
    if not text or not text.strip():
        raise CsvEmptyError("CSV пустой")

    used_delimiter = delimiter or detect_delimiter(text)
    if used_delimiter not in SUPPORTED_DELIMITERS:
        raise CsvMalformedError("Неподдерживаемый delimiter")

    reader = csv.reader(io.StringIO(text), delimiter=used_delimiter)
    try:
        parsed_rows = list(reader)
    except csv.Error as exc:
        raise CsvMalformedError(f"Некорректный CSV: {exc}") from exc

    if not parsed_rows:
        raise CsvEmptyError("CSV пустой")

    header = [col.strip() for col in parsed_rows[0]]
    if not header or any(not col for col in header):
        raise CsvInvalidHeaderError("Заголовок CSV содержит пустые имена колонок")
    if len(set(header)) != len(header):
        raise CsvInvalidHeaderError("Заголовок CSV содержит дублирующиеся колонки")

    data_rows = parsed_rows[1:]
    result: list[dict[str, str]] = []
    for row in data_rows:
        if len(row) != len(header):
            raise CsvMalformedError("Длина строки CSV не совпадает с заголовком")
        result.append({header[idx]: value for idx, value in enumerate(row)})

    return result, header, used_delimiter
