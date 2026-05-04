import base64
import io
import re
import zipfile
from pathlib import Path
from typing import Any

from sda.core.domain.errors import FileTooLargeError, ValidationError
from sda.core.similar.postprocess import postprocess_similar_rows
from sda.core.domain.limits import (
    MAX_CSV_COLUMNS,
    MAX_CSV_ROWS,
    MAX_MULTI_CSV_FILES,
    MAX_MULTI_UPLOAD_BYTES,
    MAX_UPLOAD_BYTES,
    MIN_MULTI_CSV_FILES,
)
from sda.core.similar.sdv_service import SdvSimilarService
from sda.io.csv_read import SUPPORTED_DELIMITERS, read_csv
from sda.io.csv_write import write_csv_bytes

TABLE_NAME_PATTERN = re.compile(r"[^0-9A-Za-z_]+")


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


def _build_table_name(file_name: str, used_names: set[str]) -> str:
    stem = Path(file_name).stem.strip() or "table"
    normalized = TABLE_NAME_PATTERN.sub("_", stem).strip("_").lower() or "table"
    if normalized[0].isdigit():
        normalized = f"table_{normalized}"

    candidate = normalized
    index = 2
    while candidate in used_names:
        candidate = f"{normalized}_{index}"
        index += 1
    used_names.add(candidate)
    return candidate


def _validate_multi_file_count(file_count: int) -> None:
    if file_count < MIN_MULTI_CSV_FILES:
        raise ValidationError(
            "Загрузите минимум два CSV файла для связного датасета.",
            details={
                "file_count": file_count,
                "min_file_count": MIN_MULTI_CSV_FILES,
            },
        )
    if file_count > MAX_MULTI_CSV_FILES:
        raise ValidationError(
            f"Можно загрузить не больше {MAX_MULTI_CSV_FILES} CSV файлов.",
            details={
                "file_count": file_count,
                "max_file_count": MAX_MULTI_CSV_FILES,
            },
        )


def _validate_multi_upload_size(contents: list[bytes]) -> None:
    total_bytes = sum(len(content) for content in contents)
    if total_bytes > MAX_MULTI_UPLOAD_BYTES:
        raise FileTooLargeError(
            "Суммарный размер CSV превышает допустимый лимит 25 МБ.",
            details={
                "max_upload_bytes": MAX_MULTI_UPLOAD_BYTES,
                "received_bytes": total_bytes,
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


def prepare_multi_table_similar_analysis(
    *,
    files: list[dict[str, Any]],
    preview_rows_limit: int = 5,
    delimiter: str | None = None,
    has_header: bool = True,
    service: SdvSimilarService | None = None,
) -> dict[str, Any]:
    _validate_multi_file_count(len(files))
    _validate_multi_upload_size([file["content"] for file in files])

    used_table_names: set[str] = set()
    tables: dict[str, dict[str, Any]] = {}
    for file in files:
        file_name = str(file["file_name"])
        content = bytes(file["content"])
        _validate_upload_constraints(content=content, delimiter=delimiter)
        rows, header, used_delimiter = read_csv(
            content,
            delimiter=delimiter,
            has_header=has_header,
        )
        _validate_table_shape(header=header, rows=rows)
        table_name = _build_table_name(file_name, used_table_names)
        tables[table_name] = {
            "table_name": table_name,
            "file_name": file_name,
            "rows": rows,
            "header": header,
            "delimiter": used_delimiter,
            "encoding": "utf-8",
        }

    similar_service = service or SdvSimilarService()
    analysis = similar_service.analyze_multi_table(
        tables=tables,
        preview_rows_limit=preview_rows_limit,
    )

    return {
        "tables": analysis["tables"],
        "relationships": analysis["relationships"],
        "summary": analysis["summary"],
        "warnings": analysis["warnings"],
        "stored_tables": tables,
        "metadata": analysis["metadata"],
        "table_specs": analysis["table_specs"],
        "encoding": "utf-8",
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


def run_multi_table_similar_use_case(
    *,
    analysis_id: str,
    tables: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
    table_specs: dict[str, dict[str, dict[str, Any]]],
    scale: float,
    service: SdvSimilarService | None = None,
) -> dict[str, Any]:
    if not tables:
        raise ValidationError("Невозможно построить похожий датасет по пустому набору таблиц.")
    _validate_multi_file_count(len(tables))

    for table in tables.values():
        _validate_table_shape(header=table["header"], rows=table["rows"])

    similar_service = service or SdvSimilarService()
    synthesis = similar_service.synthesize_multi_table(
        tables=tables,
        metadata_payload=metadata,
        table_specs_payload=table_specs,
        scale=scale,
    )

    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for table_summary in synthesis["table_summaries"]:
            table_name = table_summary["table_name"]
            csv_content = write_csv_bytes(
                synthesis["tables"][table_name],
                delimiter=tables[table_name]["delimiter"],
                fieldnames=tables[table_name]["header"],
            )
            archive.writestr(table_summary["file_name"], csv_content)

    return {
        "analysis_id": analysis_id,
        "file_name": "similar_dataset.zip",
        "table_count": len(tables),
        "tables": synthesis["table_summaries"],
        "result_format": "zip_base64",
        "archive_base64": base64.b64encode(zip_stream.getvalue()).decode("ascii"),
        "warnings": synthesis["warnings"],
    }
