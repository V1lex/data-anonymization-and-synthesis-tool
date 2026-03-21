import csv
import io
from collections.abc import Mapping, Sequence
from typing import Any

from sda.core.domain.errors import GenerationError

SUPPORTED_DELIMITERS = {",", ";"}


def _build_csv_text(
    rows: Sequence[Mapping[str, Any]],
    *,
    delimiter: str,
    fieldnames: Sequence[str],
) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=list(fieldnames),
        delimiter=delimiter,
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return stream.getvalue()


def write_csv_bytes(
    rows: Sequence[Mapping[str, Any]],
    *,
    delimiter: str = ",",
    fieldnames: Sequence[str] | None = None,
) -> bytes:
    """Сериализовать строки в CSV-байты UTF-8."""
    if delimiter not in SUPPORTED_DELIMITERS:
        raise GenerationError("Неподдерживаемый delimiter. Ожидались ',' или ';'.")

    if fieldnames is None:
        if not rows:
            raise GenerationError("Невозможно определить заголовок CSV для пустых строк.")
        fieldnames = list(rows[0].keys())

    return _build_csv_text(rows, delimiter=delimiter, fieldnames=fieldnames).encode("utf-8")


def write_csv(
    rows: Sequence[Mapping[str, Any]],
    header: Sequence[str] | None = None,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> bytes:
    """Совместимый интерфейс записи CSV для сценариев generate/anonymize."""
    if delimiter not in SUPPORTED_DELIMITERS:
        raise GenerationError("Неподдерживаемый delimiter. Ожидались ',' или ';'.")

    if header is None:
        if not rows:
            raise GenerationError("Невозможно определить заголовок CSV для пустых строк.")
        header = list(rows[0].keys())

    return _build_csv_text(rows, delimiter=delimiter, fieldnames=header).encode(encoding)
