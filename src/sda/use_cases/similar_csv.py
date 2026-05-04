import base64
import io
import re
import zipfile
from pathlib import Path
from typing import Any

from sda.core.domain.errors import FileTooLargeError, ValidationError
from sda.core.similar.postprocess import postprocess_similar_rows
from sda.core.domain.limits import MAX_CSV_COLUMNS, MAX_CSV_ROWS, MAX_UPLOAD_BYTES
from sda.core.similar.sdv_service import SdvSimilarService
from sda.io.csv_read import SUPPORTED_DELIMITERS, read_csv
from sda.io.csv_write import write_csv_bytes

MAX_SIMILAR_TABLES = 5
SAFE_TABLE_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_]+")


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


def _validate_table_shape(*, header: list[str], rows: list[dict[str, str]]) -> None:
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


def prepare_similar_analysis(
    *,
    file_name: str,
    content: bytes,
    preview_rows_limit: int = 5,
    delimiter: str | None = None,
    has_header: bool = True,
    service: SdvSimilarService | None = None,
) -> dict[str, Any]:
    _validate_upload_constraints(content=content, delimiter=delimiter)
    rows, header, used_delimiter = read_csv(
        content,
        delimiter=delimiter,
        has_header=has_header,
    )
    _validate_table_shape(header=header, rows=rows)

    similar_service = service or SdvSimilarService()
    analysis = similar_service.analyze(
        rows=rows,
        header=header,
        preview_rows_limit=preview_rows_limit,
    )

    return {
        "file_name": file_name,
        "row_count": len(rows),
        "column_count": len(header),
        "columns": analysis["columns"],
        "preview_rows": analysis["preview_rows"],
        "summary": analysis["summary"],
        "warnings": analysis["warnings"],
        "delimiter": used_delimiter,
        "encoding": "utf-8",
        "rows": rows,
        "header": header,
        "metadata": analysis["metadata"],
        "column_specs": analysis["column_specs"],
    }


def prepare_similar_multi_analysis(
    *,
    files: list[dict[str, Any]],
    preview_rows_limit: int = 5,
    delimiter: str | None = None,
    has_header: bool = True,
    service: SdvSimilarService | None = None,
) -> dict[str, Any]:
    if len(files) < 2:
        raise ValidationError("Для multi-table Similar нужно передать минимум два CSV-файла.")
    if len(files) > MAX_SIMILAR_TABLES:
        raise ValidationError(
            f"Слишком много таблиц для multi-table Similar: {len(files)}. Максимум {MAX_SIMILAR_TABLES}.",
            details={
                "table_count": len(files),
                "max_table_count": MAX_SIMILAR_TABLES,
            },
        )

    similar_service = service or SdvSimilarService()
    used_table_names: set[str] = set()
    tables: list[dict[str, Any]] = []
    total_rows = 0
    warnings: list[str] = []

    for file_item in files:
        file_name = str(file_item.get("file_name") or "uploaded.csv")
        content = file_item.get("content")
        if not isinstance(content, bytes):
            raise ValidationError(
                "Каждый элемент files должен содержать CSV content в bytes.",
                details={"file_name": file_name},
            )

        _validate_upload_constraints(content=content, delimiter=delimiter)
        rows, header, used_delimiter = read_csv(
            content,
            delimiter=delimiter,
            has_header=has_header,
        )
        _validate_table_shape(header=header, rows=rows)
        total_rows += len(rows)
        if total_rows > MAX_CSV_ROWS:
            raise ValidationError(
                f"Суммарное число строк в multi-table Similar превышает {MAX_CSV_ROWS}.",
                details={
                    "total_rows": total_rows,
                    "max_total_rows": MAX_CSV_ROWS,
                },
            )

        analysis = similar_service.analyze(
            rows=rows,
            header=header,
            preview_rows_limit=preview_rows_limit,
        )
        table_name = _safe_table_name(file_name=file_name, used_names=used_table_names)
        used_table_names.add(table_name)
        tables.append(
            {
                "table_name": table_name,
                "file_name": file_name,
                "row_count": len(rows),
                "column_count": len(header),
                "columns": analysis["columns"],
                "preview_rows": analysis["preview_rows"],
                "summary": analysis["summary"],
                "warnings": analysis["warnings"],
                "delimiter": used_delimiter,
                "encoding": "utf-8",
                "rows": rows,
                "header": header,
                "metadata": analysis["metadata"],
                "column_specs": analysis["column_specs"],
            }
        )
        warnings.extend(analysis["warnings"])

    relationships = _infer_relationships(tables)
    if not relationships:
        warnings.append("Не удалось автоматически найти связи между таблицами; генерация будет менее согласованной.")

    return {
        "tables": tables,
        "relationships": relationships,
        "warnings": warnings[:10],
    }


def run_similar_use_case(
    *,
    analysis_id: str,
    file_name: str,
    rows: list[dict[str, str]],
    header: list[str],
    delimiter: str,
    metadata: dict[str, Any],
    column_specs: dict[str, dict[str, Any]],
    target_rows: int,
    service: SdvSimilarService | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValidationError("Невозможно построить похожий CSV по пустому исходному набору.")
    _validate_table_shape(header=header, rows=rows)

    similar_service = service or SdvSimilarService()
    synthesis = similar_service.synthesize(
        rows=rows,
        header=header,
        metadata_payload=metadata,
        column_specs_payload=column_specs,
        target_rows=target_rows,
    )
    postprocessed_rows, postprocess_warnings = postprocess_similar_rows(
        synthesis["rows"],
        header=list(header),
    )

    csv_content = write_csv_bytes(
        postprocessed_rows,
        delimiter=delimiter,
        fieldnames=header,
    )
    file_path = Path(file_name)
    output_name = f"{file_path.stem}_similar.csv"

    return {
        "analysis_id": analysis_id,
        "file_name": output_name,
        "row_count": target_rows,
        "column_count": len(header),
        "result_format": "csv_base64",
        "content_base64": base64.b64encode(csv_content).decode("ascii"),
        "warnings": [*synthesis["warnings"], *postprocess_warnings][:10],
    }


def run_similar_group_use_case(
    *,
    group_id: str,
    tables: list[dict[str, Any]],
    relationships: list[dict[str, str]],
    target_rows_by_table: dict[str, int] | None = None,
    service: SdvSimilarService | None = None,
) -> dict[str, Any]:
    if len(tables) < 2:
        raise ValidationError("Для group Similar нужно минимум две таблицы.")

    normalized_targets = _normalize_target_rows_by_table(
        tables=tables,
        target_rows_by_table=target_rows_by_table or {},
    )
    table_payloads = {
        table["table_name"]: {
            "rows": table["rows"],
            "header": table["header"],
            "column_specs": table["column_specs"],
        }
        for table in tables
    }

    similar_service = service or SdvSimilarService()
    synthesis = similar_service.synthesize_multi(
        tables=table_payloads,
        relationships=relationships,
        target_rows_by_table=normalized_targets,
    )

    generated_files: list[dict[str, Any]] = []
    warnings: list[str] = list(synthesis["warnings"])
    table_by_name = {table["table_name"]: table for table in tables}

    for table_name, rows in synthesis["tables"].items():
        source_table = table_by_name[table_name]
        postprocessed_rows, postprocess_warnings = postprocess_similar_rows(
            rows,
            header=list(source_table["header"]),
        )
        warnings.extend(postprocess_warnings)
        csv_content = write_csv_bytes(
            postprocessed_rows,
            delimiter=source_table["delimiter"],
            fieldnames=source_table["header"],
        )
        generated_files.append(
            {
                "table_name": table_name,
                "file_name": f"{table_name}_similar.csv",
                "row_count": len(postprocessed_rows),
                "column_count": len(source_table["header"]),
                "content_type": "text/csv",
                "content": csv_content,
            }
        )

    archive_content = _zip_similar_files(generated_files)
    total_rows = sum(item["row_count"] for item in generated_files)
    return {
        "group_id": group_id,
        "file_name": "similar_bundle.zip",
        "result_format": "zip_base64",
        "generated_files": [
            {
                "table_name": item["table_name"],
                "file_name": item["file_name"],
                "row_count": item["row_count"],
                "column_count": item["column_count"],
                "content_type": item["content_type"],
            }
            for item in generated_files
        ],
        "total_rows": total_rows,
        "archive_base64": base64.b64encode(archive_content).decode("ascii"),
        "relationships": relationships,
        "warnings": warnings[:10],
    }


def _safe_table_name(*, file_name: str, used_names: set[str]) -> str:
    stem = Path(file_name).stem.strip().lower() or "table"
    normalized = SAFE_TABLE_NAME_PATTERN.sub("_", stem).strip("_") or "table"
    table_name = normalized
    suffix = 2
    while table_name in used_names:
        table_name = f"{normalized}_{suffix}"
        suffix += 1
    return table_name


def _infer_relationships(tables: list[dict[str, Any]]) -> list[dict[str, str]]:
    primary_keys = {
        table["table_name"]: _choose_primary_key(table)
        for table in tables
    }
    relationships: list[dict[str, str]] = []

    for parent in tables:
        parent_table_name = parent["table_name"]
        parent_primary_key = primary_keys[parent_table_name]
        if parent_primary_key is None:
            continue

        parent_values = set(_non_empty_values(parent["rows"], parent_primary_key))
        if not parent_values:
            continue

        for child in tables:
            child_table_name = child["table_name"]
            if child_table_name == parent_table_name:
                continue
            for child_foreign_key in _relationship_candidate_columns(
                parent_table_name=parent_table_name,
                parent_primary_key=parent_primary_key,
                child_header=child["header"],
            ):
                if child_foreign_key == primary_keys[child_table_name]:
                    continue
                child_values = set(_non_empty_values(child["rows"], child_foreign_key))
                if child_values and child_values.issubset(parent_values):
                    relationships.append(
                        {
                            "parent_table_name": parent_table_name,
                            "parent_primary_key": parent_primary_key,
                            "child_table_name": child_table_name,
                            "child_foreign_key": child_foreign_key,
                        }
                    )
                    break

    return relationships


def _choose_primary_key(table: dict[str, Any]) -> str | None:
    table_name = str(table["table_name"])
    preferred_names = [f"{_singularize_table_name(table_name)}_id", "id"]
    id_columns = [
        column_name
        for column_name, spec in table["column_specs"].items()
        if spec.get("sdtype") == "id" and _column_values_are_unique(table["rows"], column_name)
    ]
    for preferred_name in preferred_names:
        if preferred_name in id_columns:
            return preferred_name
    return id_columns[0] if id_columns else None


def _relationship_candidate_columns(
    *,
    parent_table_name: str,
    parent_primary_key: str,
    child_header: list[str],
) -> list[str]:
    candidates = [
        parent_primary_key,
        f"{_singularize_table_name(parent_table_name)}_id",
    ]
    return [
        candidate
        for candidate in dict.fromkeys(candidates)
        if candidate in child_header
    ]


def _singularize_table_name(table_name: str) -> str:
    if table_name.endswith("ies") and len(table_name) > 3:
        return f"{table_name[:-3]}y"
    if table_name.endswith("s") and len(table_name) > 1:
        return table_name[:-1]
    return table_name


def _column_values_are_unique(rows: list[dict[str, str]], column_name: str) -> bool:
    values = _non_empty_values(rows, column_name)
    return bool(values) and len(set(values)) == len(values)


def _non_empty_values(rows: list[dict[str, str]], column_name: str) -> list[str]:
    return [
        str(row.get(column_name, "")).strip()
        for row in rows
        if str(row.get(column_name, "")).strip()
    ]


def _normalize_target_rows_by_table(
    *,
    tables: list[dict[str, Any]],
    target_rows_by_table: dict[str, int],
) -> dict[str, int]:
    normalized: dict[str, int] = {}
    known_table_names = {table["table_name"] for table in tables}
    unknown_table_names = sorted(set(target_rows_by_table) - known_table_names)
    if unknown_table_names:
        raise ValidationError(
            "target_rows_by_table содержит неизвестные таблицы.",
            details={"unknown_table_names": unknown_table_names},
        )

    for table in tables:
        table_name = table["table_name"]
        target_rows = target_rows_by_table.get(table_name, table["row_count"])
        if not isinstance(target_rows, int):
            raise ValidationError(
                f"target_rows для таблицы '{table_name}' должен быть целым числом.",
                details={"table_name": table_name},
            )
        if target_rows <= 0 or target_rows > MAX_CSV_ROWS:
            raise ValidationError(
                f"target_rows для таблицы '{table_name}' должен быть от 1 до {MAX_CSV_ROWS}.",
                details={
                    "table_name": table_name,
                    "target_rows": target_rows,
                    "max_rows": MAX_CSV_ROWS,
                },
            )
        normalized[table_name] = target_rows
    return normalized


def _zip_similar_files(files: list[dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.writestr(item["file_name"], item["content"])
    return buffer.getvalue()
