import csv
import io
from typing import Any, BinaryIO, TextIO

from sda.core.domain.errors import CsvEmptyError, CsvInvalidHeaderError, CsvMalformedError

SUPPORTED_DELIMITERS = (",", ";")
UTF8_ENCODINGS = {"utf-8", "utf8", "utf-8-sig"}
FALLBACK_ENCODINGS = ("utf-8-sig", "utf-8", "cp1251")
BOM = "\ufeff"


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


def _decode_bytes(data: bytes, *, encoding: str) -> str:
    encodings = FALLBACK_ENCODINGS if encoding.lower() in UTF8_ENCODINGS else (encoding,)
    last_error: UnicodeDecodeError | None = None

    for candidate in encodings:
        try:
            return data.decode(candidate)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise CsvMalformedError("Не удалось декодировать CSV.") from last_error


def _strip_bom(text: str) -> str:
    return text.lstrip(BOM)


def _is_empty_row(row: list[str]) -> bool:
    return not row or all(not value.strip() for value in row)


def _read_file_like(source: Any, encoding: str = "utf-8") -> str:
    """Прочитать bytes/str/file-like и вернуть unicode-строку."""
    if hasattr(source, "seek"):
        source.seek(0)

    if isinstance(source, str):
        return _strip_bom(source)

    if isinstance(source, bytes):
        return _strip_bom(_decode_bytes(source, encoding=encoding))

    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, bytes):
            return _strip_bom(_decode_bytes(raw, encoding=encoding))
        return _strip_bom(str(raw))

    raise TypeError("source должен быть bytes, str или file-like объектом")


def read_csv(
    source: bytes | str | BinaryIO | TextIO,
    delimiter: str | None = None,
    encoding: str = "utf-8",
    has_header: bool = True,
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

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=used_delimiter)
    result: list[dict[str, str]] = []
    header: list[str] | None = None

    try:
        for raw_row in reader:
            if _is_empty_row(raw_row):
                continue

            row = [
                _strip_bom(value) if index == 0 else value
                for index, value in enumerate(raw_row)
            ]

            if header is None:
                if has_header:
                    header = [col.strip() for col in row]
                    if not header or any(not col for col in header):
                        raise CsvInvalidHeaderError("Заголовок CSV содержит пустые имена колонок")
                    if len(set(header)) != len(header):
                        raise CsvInvalidHeaderError("Заголовок CSV содержит дублирующиеся колонки")
                    continue

                width = len(row)
                if width == 0:
                    raise CsvMalformedError("CSV не содержит колонок")
                header = [f"column_{index + 1}" for index in range(width)]

            if len(row) != len(header):
                raise CsvMalformedError("Длина строки CSV не совпадает с заголовком")
            result.append({header[idx]: value for idx, value in enumerate(row)})
    except csv.Error as exc:
        raise CsvMalformedError(f"Некорректный CSV: {exc}") from exc

    if header is None:
        raise CsvEmptyError("CSV пустой")
    if not result:
        raise CsvEmptyError("CSV не содержит строк данных")

    return result, header, used_delimiter
