import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile

from sda.core.domain.errors import (
    AnalysisFailedError,
    InvalidFileTypeError,
    SdaError,
    SynthesisFailedError,
)
from sda.use_cases.similar_csv import (
    prepare_similar_analysis,
    prepare_similar_multi_analysis,
    run_similar_group_use_case,
    run_similar_use_case,
)
from sda.web.deps import (
    SimilarAnalysisGroupStore,
    SimilarAnalysisStore,
    SimilarJobStore,
    get_similar_analysis_store,
    get_similar_group_store,
    get_similar_job_store,
)
from sda.web.schemas.similar import (
    SimilarAnalyzeResponse,
    SimilarJobCreateRequest,
    SimilarJobCreateResponse,
    SimilarJobStatusResponse,
    SimilarMultiAnalyzeResponse,
    SimilarMultiRunResponse,
    SimilarRunRequest,
    SimilarRunResponse,
    SimilarTableAnalyzeResponse,
)

router = APIRouter(prefix="/similar", tags=["similar"])
_similar_job_executor = ThreadPoolExecutor(max_workers=2)

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
            table_name=session.table_name,
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


@router.post("/analyze-multi")
async def analyze_similar_csv_group(
    files: list[UploadFile] = File(...),
    preview_rows_limit: int = Form(default=5, ge=1, le=20),
    has_header: bool = Form(default=True),
    delimiter: str | None = Form(default=None, min_length=1, max_length=1),
    store: SimilarAnalysisStore = Depends(get_similar_analysis_store),
    group_store: SimilarAnalysisGroupStore = Depends(get_similar_group_store),
) -> dict:
    file_payloads: list[dict[str, Any]] = []
    for file in files:
        file_name = file.filename or "uploaded.csv"
        if file.content_type not in CSV_CONTENT_TYPES and not file_name.lower().endswith(".csv"):
            raise InvalidFileTypeError("Загружен файл не в формате CSV.")
        file_payloads.append(
            {
                "file_name": file_name,
                "content": await file.read(),
            }
        )

    try:
        analysis = prepare_similar_multi_analysis(
            files=file_payloads,
            preview_rows_limit=preview_rows_limit,
            delimiter=delimiter,
            has_header=has_header,
        )
        table_responses: list[dict] = []
        analysis_ids: list[str] = []
        for table in analysis["tables"]:
            session = store.create(
                file_name=table["file_name"],
                table_name=table["table_name"],
                rows=table["rows"],
                header=table["header"],
                delimiter=table["delimiter"],
                metadata=table["metadata"],
                column_specs=table["column_specs"],
                encoding=table["encoding"],
            )
            analysis_ids.append(session.analysis_id)
            table_responses.append(
                SimilarTableAnalyzeResponse(
                    analysis_id=session.analysis_id,
                    table_name=session.table_name,
                    file_name=table["file_name"],
                    row_count=table["row_count"],
                    column_count=table["column_count"],
                    columns=table["columns"],
                    preview_rows=table["preview_rows"],
                    summary=table["summary"],
                    warnings=table["warnings"],
                ).model_dump()
            )

        group = group_store.create(
            analysis_ids=analysis_ids,
            relationships=analysis["relationships"],
        )
        response = SimilarMultiAnalyzeResponse(
            group_id=group.group_id,
            tables=table_responses,
            relationships=analysis["relationships"],
            warnings=analysis["warnings"],
        )
        return response.model_dump()
    except SdaError:
        raise
    except Exception as exc:
        raise AnalysisFailedError("Не удалось проанализировать CSV-группу для Similar.") from exc


@router.post("/jobs", status_code=202)
def create_similar_job(
    request: SimilarJobCreateRequest,
    store: SimilarAnalysisStore = Depends(get_similar_analysis_store),
    group_store: SimilarAnalysisGroupStore = Depends(get_similar_group_store),
    job_store: SimilarJobStore = Depends(get_similar_job_store),
) -> dict:
    if request.analysis_id is not None:
        store.get(request.analysis_id)
        job = job_store.create_single(
            analysis_id=request.analysis_id,
            target_rows=int(request.target_rows),
        )
    else:
        group = group_store.get(str(request.group_id))
        for analysis_id in group.analysis_ids:
            store.get(analysis_id)
        job = job_store.create_group(
            group_id=group.group_id,
            target_rows_by_table=request.target_rows_by_table,
        )

    _similar_job_executor.submit(
        _run_similar_job,
        job.job_id,
        store,
        group_store,
        job_store,
    )
    response = SimilarJobCreateResponse(
        job_id=job.job_id,
        status=job.status,
        status_url=f"/api/v1/similar/jobs/{job.job_id}",
    )
    return response.model_dump()


@router.get("/jobs/{job_id}")
def get_similar_job(
    job_id: str,
    job_store: SimilarJobStore = Depends(get_similar_job_store),
) -> dict:
    return _build_job_status_response(job_store.get(job_id)).model_dump()


def _run_similar_job(
    job_id: str,
    store: SimilarAnalysisStore,
    group_store: SimilarAnalysisGroupStore,
    job_store: SimilarJobStore,
) -> None:
    try:
        job = job_store.update(
            job_id,
            status="running",
            progress=0.1,
            started_at=time.time(),
            error=None,
        )
        if job.kind == "single_table":
            session = store.get(str(job.analysis_id))
            result = run_similar_use_case(
                analysis_id=session.analysis_id,
                file_name=session.file_name,
                rows=session.rows,
                header=session.header,
                delimiter=session.delimiter,
                metadata=session.metadata,
                column_specs=session.column_specs,
                target_rows=int(job.target_rows),
            )
            result_payload = SimilarRunResponse(**result).model_dump()
        else:
            group = group_store.get(str(job.group_id))
            table_sessions = [store.get(analysis_id) for analysis_id in group.analysis_ids]
            result = run_similar_group_use_case(
                group_id=group.group_id,
                tables=[_session_to_table_payload(session) for session in table_sessions],
                relationships=group.relationships,
                target_rows_by_table=job.target_rows_by_table,
            )
            result_payload = SimilarMultiRunResponse(**result).model_dump()

        job_store.update(
            job_id,
            status="succeeded",
            progress=1.0,
            result=result_payload,
            finished_at=time.time(),
        )
    except SdaError as exc:
        job_store.update(
            job_id,
            status="failed",
            progress=1.0,
            error={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
            finished_at=time.time(),
        )
    except Exception as exc:
        job_store.update(
            job_id,
            status="failed",
            progress=1.0,
            error={
                "error_code": "synthesis_failed",
                "message": "Не удалось выполнить Similar job.",
                "details": {"exception": str(exc)},
            },
            finished_at=time.time(),
        )


def _session_to_table_payload(session) -> dict[str, Any]:
    return {
        "analysis_id": session.analysis_id,
        "file_name": session.file_name,
        "table_name": session.table_name,
        "row_count": len(session.rows),
        "column_count": len(session.header),
        "rows": session.rows,
        "header": session.header,
        "delimiter": session.delimiter,
        "metadata": session.metadata,
        "column_specs": session.column_specs,
    }


def _build_job_status_response(job) -> SimilarJobStatusResponse:
    return SimilarJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        kind=job.kind,
        progress=job.progress,
        analysis_id=job.analysis_id,
        group_id=job.group_id,
        target_rows=job.target_rows,
        target_rows_by_table=job.target_rows_by_table,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        updated_at=job.updated_at,
    )
