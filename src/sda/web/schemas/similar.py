from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sda.web.schemas.generate import ErrorResponse, ResultFormat

MAX_SIMILAR_ROWS = 10_000
MAX_SIMILAR_COLUMNS = 128
MAX_SIMILAR_TABLES = 5


class SimilarColumnProfile(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    inferred_type: str = Field(..., min_length=1, max_length=32)
    null_ratio: float = Field(..., ge=0.0, le=1.0)
    unique_ratio: float = Field(..., ge=0.0, le=1.0)
    sample_values: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("column name must not be blank")
        if any(char in normalized for char in "\r\n\t"):
            raise ValueError("column name must not contain control characters")
        return normalized


class SimilarAnalyzeRequest(BaseModel):
    preview_rows_limit: int = Field(default=5, ge=1, le=20)
    has_header: bool = Field(default=True)
    delimiter: str = Field(default=",", min_length=1, max_length=1)


class SimilarAnalyzeResponse(BaseModel):
    analysis_id: str = Field(..., min_length=1, max_length=64)
    table_name: str = Field(..., min_length=1, max_length=128)
    file_name: str = Field(..., min_length=1, max_length=256)
    row_count: int = Field(..., ge=1, le=MAX_SIMILAR_ROWS)
    column_count: int = Field(..., ge=1, le=MAX_SIMILAR_COLUMNS)
    columns: list[SimilarColumnProfile] = Field(..., min_length=1, max_length=MAX_SIMILAR_COLUMNS)
    preview_rows: list[dict[str, str | None]] = Field(default_factory=list, max_length=5)
    summary: list[str] = Field(default_factory=list, max_length=10)
    warnings: list[str] = Field(default_factory=list, max_length=10)


class SimilarRelationship(BaseModel):
    parent_table_name: str = Field(..., min_length=1, max_length=128)
    parent_primary_key: str = Field(..., min_length=1, max_length=128)
    child_table_name: str = Field(..., min_length=1, max_length=128)
    child_foreign_key: str = Field(..., min_length=1, max_length=128)


class SimilarTableAnalyzeResponse(SimilarAnalyzeResponse):
    pass


class SimilarMultiAnalyzeResponse(BaseModel):
    group_id: str = Field(..., min_length=1, max_length=64)
    tables: list[SimilarTableAnalyzeResponse] = Field(..., min_length=2, max_length=MAX_SIMILAR_TABLES)
    relationships: list[SimilarRelationship] = Field(default_factory=list, max_length=16)
    warnings: list[str] = Field(default_factory=list, max_length=10)


class SimilarRunRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    analysis_id: str = Field(..., min_length=1, max_length=64)
    target_rows: int = Field(..., ge=1, le=MAX_SIMILAR_ROWS)


class SimilarRunResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    analysis_id: str = Field(..., min_length=1, max_length=64)
    file_name: str = Field(..., min_length=1, max_length=128)
    row_count: int = Field(..., ge=1, le=MAX_SIMILAR_ROWS)
    column_count: int = Field(..., ge=1, le=MAX_SIMILAR_COLUMNS)
    result_format: ResultFormat = Field(default=ResultFormat.CSV_BASE64)
    content_base64: str = Field(..., min_length=1)
    warnings: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_result_format(self) -> "SimilarRunResponse":
        if self.result_format != ResultFormat.CSV_BASE64:
            raise ValueError("similar responses support only csv_base64")
        return self


class SimilarGeneratedFile(BaseModel):
    table_name: str = Field(..., min_length=1, max_length=128)
    file_name: str = Field(..., min_length=1, max_length=128)
    row_count: int = Field(..., ge=1, le=MAX_SIMILAR_ROWS)
    column_count: int = Field(..., ge=1, le=MAX_SIMILAR_COLUMNS)
    content_type: str = Field(default="text/csv")


class SimilarMultiRunResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    group_id: str = Field(..., min_length=1, max_length=64)
    file_name: str = Field(..., min_length=1, max_length=128)
    result_format: ResultFormat = Field(default=ResultFormat.ZIP_BASE64)
    generated_files: list[SimilarGeneratedFile] = Field(..., min_length=2, max_length=MAX_SIMILAR_TABLES)
    total_rows: int = Field(..., ge=1, le=MAX_SIMILAR_ROWS * MAX_SIMILAR_TABLES)
    archive_base64: str = Field(..., min_length=1)
    relationships: list[SimilarRelationship] = Field(default_factory=list, max_length=16)
    warnings: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_result_format(self) -> "SimilarMultiRunResponse":
        if self.result_format != ResultFormat.ZIP_BASE64:
            raise ValueError("multi-table similar responses support only zip_base64")
        return self


class SimilarJobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SimilarJobCreateRequest(BaseModel):
    analysis_id: str | None = Field(default=None, min_length=1, max_length=64)
    group_id: str | None = Field(default=None, min_length=1, max_length=64)
    target_rows: int | None = Field(default=None, ge=1, le=MAX_SIMILAR_ROWS)
    target_rows_by_table: dict[str, int] = Field(default_factory=dict, max_length=MAX_SIMILAR_TABLES)

    @model_validator(mode="after")
    def validate_job_target(self) -> "SimilarJobCreateRequest":
        if bool(self.analysis_id) == bool(self.group_id):
            raise ValueError("pass exactly one of analysis_id or group_id")
        if self.analysis_id and self.target_rows is None:
            raise ValueError("target_rows is required for single-table jobs")
        if self.analysis_id and self.target_rows_by_table:
            raise ValueError("target_rows_by_table is supported only for group jobs")
        if self.group_id and self.target_rows is not None:
            raise ValueError("target_rows is supported only for single-table jobs")
        for table_name, row_count in self.target_rows_by_table.items():
            if not table_name.strip():
                raise ValueError("target_rows_by_table keys must not be blank")
            if row_count <= 0 or row_count > MAX_SIMILAR_ROWS:
                raise ValueError(f"target_rows_by_table values must be between 1 and {MAX_SIMILAR_ROWS}")
        return self


class SimilarJobCreateResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    job_id: str = Field(..., min_length=1, max_length=64)
    status: SimilarJobStatus
    status_url: str = Field(..., min_length=1, max_length=256)


class SimilarJobStatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    job_id: str = Field(..., min_length=1, max_length=64)
    status: SimilarJobStatus
    kind: str = Field(..., min_length=1, max_length=32)
    progress: float = Field(..., ge=0.0, le=1.0)
    analysis_id: str | None = Field(default=None, min_length=1, max_length=64)
    group_id: str | None = Field(default=None, min_length=1, max_length=64)
    target_rows: int | None = Field(default=None, ge=1, le=MAX_SIMILAR_ROWS)
    target_rows_by_table: dict[str, int] = Field(default_factory=dict)
    result: dict[str, Any] | None = Field(default=None)
    error: dict[str, Any] | None = Field(default=None)
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    updated_at: float


__all__ = [
    "ErrorResponse",
    "ResultFormat",
    "SimilarAnalyzeRequest",
    "SimilarAnalyzeResponse",
    "SimilarColumnProfile",
    "SimilarGeneratedFile",
    "SimilarJobCreateRequest",
    "SimilarJobCreateResponse",
    "SimilarJobStatus",
    "SimilarJobStatusResponse",
    "SimilarMultiAnalyzeResponse",
    "SimilarMultiRunResponse",
    "SimilarRelationship",
    "SimilarRunRequest",
    "SimilarRunResponse",
    "SimilarTableAnalyzeResponse",
]
