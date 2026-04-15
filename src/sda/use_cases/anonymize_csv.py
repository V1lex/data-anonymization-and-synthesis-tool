import base64
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sda.core.anonymization.field_detector import FieldDetector
from sda.core.anonymization.anonymizer import CsvAnonymizer
from sda.core.anonymization.rules import ensure_supported_method, get_method_title, get_supported_methods
from sda.core.domain.errors import FileTooLargeError, InvalidRuleError, UnknownColumnError, ValidationError
from sda.core.domain.limits import MAX_CSV_COLUMNS, MAX_CSV_ROWS, MAX_UPLOAD_BYTES
from sda.io.csv_read import SUPPORTED_DELIMITERS, read_csv
from sda.io.csv_write import write_csv_bytes
from sda.use_cases.analyze_columns import analyze_columns


DATE_LIKE_TYPES = {"birth_date", "date", "datetime"}
TEXT_LIKE_TYPES = {"email", "phone", "full_name", "address", "vehicle_plate", "id_like", "text", "city", "category"}


def _detect_type(column_name: str, values: Sequence[str]) -> str:
    detector = FieldDetector()
    detection = detector.detect(
        column_name=column_name,
        values=[str(value) for value in values if value is not None],
    )
    return detection.detected_type


def _get_method_compatibility_error(*, column_name: str, method: str, values: Sequence[str]) -> tuple[str | None, str]:
    non_empty_values = [value.strip() for value in values if value and value.strip()]
    if not non_empty_values:
        return None, "text"

    detected_type = _detect_type(column_name, non_empty_values)
    method_title = get_method_title(method)

    if method == "generalize_year":
        if detected_type not in DATE_LIKE_TYPES:
            return (
                f"Метод '{method_title}' нельзя применить к колонке '{column_name}': значения не похожи на даты.",
                detected_type,
            )
        return None, detected_type

    if method == "pseudonymize":
        if detected_type in DATE_LIKE_TYPES:
            return (
                f"Метод '{method_title}' не подходит для колонки '{column_name}': для дат используйте 'Обобщение до года' или 'Скрытие'.",
                detected_type,
            )
        if detected_type == "boolean":
            return (
                f"Метод '{method_title}' не подходит для колонки '{column_name}': булевы значения лучше оставить без изменений или скрыть.",
                detected_type,
            )
        if detected_type == "number":
            return (
                f"Метод '{method_title}' не подходит для числовой колонки '{column_name}': используйте 'Скрытие' или оставьте значение без изменений.",
                detected_type,
            )
        return None, detected_type

    if method == "mask":
        if detected_type in DATE_LIKE_TYPES:
            return (
                f"Метод '{method_title}' не подходит для колонки '{column_name}': для дат используйте 'Обобщение до года' или 'Скрытие'.",
                detected_type,
            )
        if detected_type == "boolean":
            return (
                f"Метод '{method_title}' не подходит для колонки '{column_name}': булевы значения лучше оставить без изменений или скрыть.",
                detected_type,
            )
        if detected_type == "number":
            return (
                f"Метод '{method_title}' не подходит для числовой колонки '{column_name}': он рассчитан на текст, email, телефоны и идентификаторы.",
                detected_type,
            )
        return None, detected_type

    return None, detected_type


def _validate_rule_applicability(*, column_name: str, method: str, values: Sequence[str]) -> None:
    error_message, inferred_type = _get_method_compatibility_error(
        column_name=column_name,
        method=method,
        values=values,
    )
    if error_message is None:
        return
    raise InvalidRuleError(
        error_message,
        details={
            "column_name": column_name,
            "method": method,
            "inferred_type": inferred_type,
        },
    )


def _build_unsupported_methods(column_name: str, values: Sequence[str]) -> dict[str, str]:
    unsupported_methods: dict[str, str] = {}
    for method in get_supported_methods():
        error_message, _ = _get_method_compatibility_error(
            column_name=column_name,
            method=method,
            values=values,
        )
        if error_message is not None:
            unsupported_methods[method] = error_message
    return unsupported_methods


def _build_uploaded_columns(header: Sequence[str], rows: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    column_descriptions = analyze_columns(header=header, rows=rows)
    for column in column_descriptions:
        values = [row.get(column["name"], "") for row in rows]
        column["unsupported_methods"] = _build_unsupported_methods(column["name"], values)
    return column_descriptions


def _validate_upload_constraints(*, content: bytes, delimiter: str | None) -> None:
    if len(content) > MAX_UPLOAD_BYTES:
        raise FileTooLargeError(
            "Размер CSV превышает допустимый лимит 5 МБ.",
            details={
                "max_upload_bytes": MAX_UPLOAD_BYTES,
                "received_bytes": len(content),
            },
        )

    if delimiter is not None and delimiter not in SUPPORTED_DELIMITERS:
        raise ValidationError(
            "Неподдерживаемый delimiter. Ожидались ',' или ';'.",
            details={
                "delimiter": delimiter,
                "supported_delimiters": list(SUPPORTED_DELIMITERS),
            },
        )


def _validate_table_shape(*, header: Sequence[str], rows: Sequence[dict[str, str]]) -> None:
    if len(header) > MAX_CSV_COLUMNS:
        raise ValidationError(
            f"CSV содержит слишком много колонок: {len(header)}. Максимум {MAX_CSV_COLUMNS}.",
            details={
                "column_count": len(header),
                "max_column_count": MAX_CSV_COLUMNS,
            },
        )

    if len(rows) > MAX_CSV_ROWS:
        raise ValidationError(
            f"CSV содержит слишком много строк: {len(rows)}. Максимум {MAX_CSV_ROWS}.",
            details={
                "row_count": len(rows),
                "max_row_count": MAX_CSV_ROWS,
            },
        )


def prepare_anonymize_upload(
    *,
    file_name: str,
    content: bytes,
    delimiter: str | None = None,
    has_header: bool = True,
) -> dict[str, Any]:
    _validate_upload_constraints(content=content, delimiter=delimiter)
    rows, header, used_delimiter = read_csv(
        content,
        delimiter=delimiter,
        has_header=has_header,
    )
    _validate_table_shape(header=header, rows=rows)
    preview_rows = rows[:5]
    return {
        "file_name": file_name,
        "row_count": len(rows),
        "column_count": len(header),
        "columns": _build_uploaded_columns(header, rows),
        "preview_rows": preview_rows,
        "delimiter": used_delimiter,
        "encoding": "utf-8",
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
    _validate_table_shape(header=header, rows=rows)

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
        sample_values = [row.get(column_name, "") for row in rows]
        _validate_rule_applicability(
            column_name=column_name,
            method=method,
            values=sample_values,
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
