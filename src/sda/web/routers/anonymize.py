from fastapi import APIRouter, Depends, File, Form, UploadFile

from sda.core.domain.errors import InvalidFileTypeError
from sda.use_cases.anonymize_csv import prepare_anonymize_upload, run_anonymize_use_case
from sda.web.deps import UploadStore, get_upload_store
from sda.web.schemas.anonymize import AnonymizeRunRequest, AnonymizeRunResponse, AnonymizeUploadResponse

router = APIRouter(prefix="/anonymize", tags=["anonymize"])

CSV_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
}


@router.post("/upload")
async def upload_anonymize_csv(
    file: UploadFile = File(...),
    delimiter: str | None = Form(default=None),
    has_header: bool = Form(default=True),
    suggest: bool = Form(default=True),
    store: UploadStore = Depends(get_upload_store),
) -> dict:
    file_name = file.filename or "uploaded.csv"
    if file.content_type not in CSV_CONTENT_TYPES and not file_name.lower().endswith(".csv"):
        raise InvalidFileTypeError("Загружен файл не в формате CSV.")

    content = await file.read()
    upload_data = prepare_anonymize_upload(
        file_name=file_name,
        content=content,
        delimiter=delimiter,
        has_header=has_header,
        suggest=suggest,
    )
    session = store.create(
        file_name=upload_data["file_name"],
        rows=upload_data["rows"],
        header=upload_data["header"],
        delimiter=upload_data["delimiter"],
        encoding=upload_data["encoding"],
    )

    response = AnonymizeUploadResponse(
        upload_id=session.upload_id,
        file_name=upload_data["file_name"],
        row_count=upload_data["row_count"],
        column_count=upload_data["column_count"],
        columns=upload_data["columns"],
        preview_rows=upload_data["preview_rows"],
        delimiter=upload_data["delimiter"],
        encoding=upload_data["encoding"],
        suggestions_included=upload_data["suggestions_included"],
        warnings=upload_data["warnings"],
    )
    return response.model_dump()


@router.post("/run")
def run_anonymize(
    request: AnonymizeRunRequest,
    store: UploadStore = Depends(get_upload_store),
) -> dict:
    session = store.get(request.upload_id)
    result = run_anonymize_use_case(
        upload_id=session.upload_id,
        file_name=session.file_name,
        rows=session.rows,
        header=session.header,
        delimiter=session.delimiter,
        rules=[rule.model_dump() for rule in request.rules],
    )
    return AnonymizeRunResponse(**result).model_dump()
