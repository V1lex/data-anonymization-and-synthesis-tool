import base64
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sda.core.anonymization.anonymizer import CsvAnonymizer
from sda.core.anonymization.rules import ensure_supported_method
from sda.core.domain.errors import InvalidRuleError, UnknownColumnError, ValidationError
from sda.io.csv_read import read_csv
from sda.io.csv_write import write_csv_bytes

SUGGESTED_METHODS: tuple[tuple[str, str, str], ...] = (
    ("email", "mask", "column name looks like email"),
    ("phone", "mask", "column name looks like phone"),
    ("name", "pseudonymize", "column name looks like a personal name"),
    ("address", "redact", "column name looks like address"),
    ("birth", "generalize_year", "column name looks like birth date"),
)


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _extract_year(value: str) -> str | None:
    for token in (value, value[:10]):
        for chunk in token.replace("/", "-").replace(".", "-").split("-"):
            if len(chunk) == 4 and chunk.isdigit():
                return chunk
    return None


def _infer_type(values: Sequence[str]) -> str:
    non_empty = [value.strip() for value in values if value is not None and value.strip()]
    if not non_empty:
        return "string"
    if all(_is_number(value) for value in non_empty):
        return "number"
    if all(_extract_year(value) for value in non_empty):
        return "date"
    lowered = {value.lower() for value in non_empty}
    if lowered.issubset({"true", "false", "0", "1", "yes", "no"}):
        return "boolean"
    return "string"


def _build_suggestion(column_name: str, sample_values: Sequence[str]) -> tuple[str | None, float | None, str | None]:
    lowered_name = column_name.lower()
    for needle, method, hint in SUGGESTED_METHODS:
        if needle in lowered_name:
            return method, 0.91, hint

    if any("@" in sample for sample in sample_values):
        return "mask", 0.85, "sample values look like email"
    if any(sample.strip().startswith("+") and sum(char.isdigit() for char in sample) >= 10 for sample in sample_values):
        return "mask", 0.84, "sample values look like phone"
    return None, None, None


def _build_uploaded_columns(header: Sequence[str], rows: Sequence[dict[str, str]], suggest: bool) -> list[dict[str, Any]]:
    column_descriptions: list[dict[str, Any]] = []
    total_rows = len(rows) or 1

    for index, column_name in enumerate(header):
        values = [row.get(column_name, "") for row in rows]
        non_empty_values = [value for value in values if value.strip()]
        sample_values = non_empty_values[:2]
        unique_ratio = len(set(non_empty_values)) / max(len(non_empty_values), 1)
        null_ratio = 1.0 - (len(non_empty_values) / total_rows)
        inferred_type = _infer_type(values)
        suggested_method, confidence, pii_hint = _build_suggestion(column_name, sample_values) if suggest else (None, None, None)

        column_descriptions.append(
            {
                "index": index,
                "name": column_name,
                "inferred_type": inferred_type,
                "sample_values": sample_values,
                "null_ratio": round(null_ratio, 4),
                "unique_ratio": round(unique_ratio, 4),
                "suggested_method": suggested_method,
                "suggestion_confidence": confidence,
                "pii_hint": pii_hint,
            }
        )

    return column_descriptions


def prepare_anonymize_upload(
    *,
    file_name: str,
    content: bytes,
    delimiter: str | None = None,
    has_header: bool = True,
    suggest: bool = True,
) -> dict[str, Any]:
    rows, header, used_delimiter = read_csv(
        content,
        delimiter=delimiter,
        has_header=has_header,
    )
    preview_rows = rows[:5]
    return {
        "file_name": file_name,
        "row_count": len(rows),
        "column_count": len(header),
        "columns": _build_uploaded_columns(header, rows, suggest),
        "preview_rows": preview_rows,
        "delimiter": used_delimiter,
        "encoding": "utf-8",
        "suggestions_included": suggest,
        "warnings": [],
        "rows": rows,
        "header": header,
    }


def run_anonymize_use_case(
    *,
    upload_id: str,
    file_name: str,
    rows: Sequence[dict[str, str]],
    header: Sequence[str],
    delimiter: str,
    rules: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    if not rows:
        raise ValidationError("Невозможно анонимизировать пустой CSV.")

    seen_columns: set[str] = set()
    normalized_rules: dict[str, dict[str, Any]] = {}
    for rule in rules:
        column_name = str(rule.get("column_name", "")).strip()
        if not column_name:
            raise ValidationError("column_name не может быть пустым.")
        if column_name in seen_columns:
            raise ValidationError(
                f"Колонка '{column_name}' указана в rules больше одного раза.",
                details={"column_name": column_name},
            )
        if column_name not in header:
            raise UnknownColumnError(
                f"Колонка '{column_name}' отсутствует во входном CSV.",
                details={"column_name": column_name},
            )

        method = ensure_supported_method(str(rule.get("method", "keep")))
        params = dict(rule.get("params") or {})

        if method == "generalize_year":
            sample_values = [row.get(column_name, "") for row in rows if row.get(column_name, "").strip()]
            if sample_values and any(_extract_year(value) is None for value in sample_values[:5]):
                raise InvalidRuleError(
                    f"Метод generalize_year не подходит для колонки '{column_name}'.",
                    details={"column_name": column_name, "method": method},
                )

        seen_columns.add(column_name)
        normalized_rules[column_name] = {
            "column_name": column_name,
            "method": method,
            "params": params,
        }

    anonymizer = CsvAnonymizer()
    anonymized_rows = anonymizer.anonymize_rows(rows, normalized_rules)
    csv_content = write_csv_bytes(
        anonymized_rows,
        delimiter=delimiter,
        fieldnames=header,
    )

    file_path = Path(file_name)
    output_name = f"{file_path.stem}_anonymized.csv"

    return {
        "upload_id": upload_id,
        "file_name": output_name,
        "row_count": len(rows),
        "column_count": len(header),
        "result_format": "csv_base64",
        "content_base64": base64.b64encode(csv_content).decode("ascii"),
        "applied_rules": [normalized_rules[column_name] for column_name in header if column_name in normalized_rules],
        "warnings": [],
    }
