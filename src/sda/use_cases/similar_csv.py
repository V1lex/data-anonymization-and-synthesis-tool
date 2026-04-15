import base64
from pathlib import Path
from typing import Any

from sda.core.domain.errors import FileTooLargeError, ValidationError
from sda.core.similar.postprocess import postprocess_similar_rows
from sda.core.domain.limits import MAX_CSV_COLUMNS, MAX_CSV_ROWS, MAX_UPLOAD_BYTES
from sda.core.similar.sdv_service import SdvSimilarService
from sda.io.csv_read import SUPPORTED_DELIMITERS, read_csv
from sda.io.csv_write import write_csv_bytes


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
