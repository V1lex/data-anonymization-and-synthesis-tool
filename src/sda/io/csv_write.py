import csv
import io
from collections.abc import Mapping, Sequence
from typing import Any

from sda.core.domain.errors import GenerationError


def write_csv_bytes(
    rows: Sequence[Mapping[str, Any]],
    *,
    delimiter: str = ",",
    fieldnames: Sequence[str] | None = None,
) -> bytes:
    """Serialize rows to UTF-8 CSV bytes."""
    if delimiter not in {",", ";"}:
        raise GenerationError("Unsupported delimiter. Expected ',' or ';'.")

    if fieldnames is None:
        if not rows:
            raise GenerationError("Cannot infer CSV header from empty rows.")
        fieldnames = list(rows[0].keys())

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

    return stream.getvalue().encode("utf-8")
