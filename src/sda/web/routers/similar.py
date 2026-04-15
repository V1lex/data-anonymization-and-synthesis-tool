from fastapi import APIRouter, Depends, File, Form, UploadFile

from sda.core.domain.errors import (
    AnalysisFailedError,
    InvalidFileTypeError,
    SdaError,
    SynthesisFailedError,
)
from sda.use_cases.similar_csv import prepare_similar_analysis, run_similar_use_case
from sda.web.deps import SimilarAnalysisStore, get_similar_analysis_store
from sda.web.schemas.similar import SimilarAnalyzeResponse, SimilarRunRequest, SimilarRunResponse

router = APIRouter(prefix="/similar", tags=["similar"])

CSV_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
}


@router.post("/analyze")
async def analyze_similar_csv(
    file: UploadFile = File(...),
    preview_rows_limit: int = Form(default=5, ge=1, le=20),
    has_header: bool = Form(default=True),
    delimiter: str | None = Form(default=None, min_length=1, max_length=1),
    store: SimilarAnalysisStore = Depends(get_similar_analysis_store),
) -> dict:
    file_name = file.filename or "uploaded.csv"
    if file.content_type not in CSV_CONTENT_TYPES and not file_name.lower().endswith(".csv"):
        raise InvalidFileTypeError("Загружен файл не в формате CSV.")

    try:
        content = await file.read()
        analysis = prepare_similar_analysis(
            file_name=file_name,
            content=content,
            preview_rows_limit=preview_rows_limit,
            delimiter=delimiter,
            has_header=has_header,
        )
        session = store.create(
            file_name=analysis["file_name"],
            rows=analysis["rows"],
            header=analysis["header"],
            delimiter=analysis["delimiter"],
            metadata=analysis["metadata"],
            column_specs=analysis["column_specs"],
            encoding=analysis["encoding"],
        )
        response = SimilarAnalyzeResponse(
            analysis_id=session.analysis_id,
            file_name=analysis["file_name"],
            row_count=analysis["row_count"],
            column_count=analysis["column_count"],
            columns=analysis["columns"],
            preview_rows=analysis["preview_rows"],
            summary=analysis["summary"],
            warnings=analysis["warnings"],
        )
        return response.model_dump()
    except SdaError:
        raise
    except Exception as exc:
        raise AnalysisFailedError("Не удалось проанализировать CSV для Similar.") from exc


@router.post("/run")
def run_similar(
    request: SimilarRunRequest,
    store: SimilarAnalysisStore = Depends(get_similar_analysis_store),
) -> dict:
    try:
        session = store.get(request.analysis_id)
        result = run_similar_use_case(
            analysis_id=session.analysis_id,
            file_name=session.file_name,
            rows=session.rows,
            header=session.header,
            delimiter=session.delimiter,
            metadata=session.metadata,
            column_specs=session.column_specs,
            target_rows=request.target_rows,
        )
        return SimilarRunResponse(**result).model_dump()
    except SdaError:
        raise
    except Exception as exc:
        raise SynthesisFailedError("Не удалось сгенерировать похожий CSV.") from exc
