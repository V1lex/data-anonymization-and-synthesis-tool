from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sda.web.schemas.generate import ErrorResponse

MAX_SIMILAR_ROWS = 10_000
MAX_SIMILAR_COLUMNS = 128


class SimilarOutputFormat(str, Enum):
    CSV_BASE64 = "csv_base64"


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
    file_name: str = Field(..., min_length=1, max_length=256)
    row_count: int = Field(..., ge=1, le=MAX_SIMILAR_ROWS)
    column_count: int = Field(..., ge=1, le=MAX_SIMILAR_COLUMNS)
    columns: list[SimilarColumnProfile] = Field(..., min_length=1, max_length=MAX_SIMILAR_COLUMNS)
    preview_rows: list[dict[str, str | None]] = Field(default_factory=list, max_length=5)
    summary: list[str] = Field(default_factory=list, max_length=10)
    warnings: list[str] = Field(default_factory=list, max_length=10)


class SimilarRunRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    analysis_id: str = Field(..., min_length=1, max_length=64)
    target_rows: int = Field(..., ge=1, le=MAX_SIMILAR_ROWS)
    output_format: SimilarOutputFormat = Field(default=SimilarOutputFormat.CSV_BASE64)
    random_seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    file_name: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("file_name must not be blank")
        if "/" in normalized or "\\" in normalized:
            raise ValueError("file_name must not contain path separators")
        if not normalized.endswith(".csv"):
            raise ValueError("file_name must end with .csv")
        return normalized


class SimilarRunResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    analysis_id: str = Field(..., min_length=1, max_length=64)
    file_name: str = Field(..., min_length=1, max_length=128)
    row_count: int = Field(..., ge=1, le=MAX_SIMILAR_ROWS)
    column_count: int = Field(..., ge=1, le=MAX_SIMILAR_COLUMNS)
    output_format: SimilarOutputFormat = Field(default=SimilarOutputFormat.CSV_BASE64)
    content_base64: str = Field(..., min_length=1)
    warnings: list[str] = Field(default_factory=list, max_length=10)


__all__ = [
    "ErrorResponse",
    "SimilarAnalyzeRequest",
    "SimilarAnalyzeResponse",
    "SimilarColumnProfile",
    "SimilarOutputFormat",
    "SimilarRunRequest",
    "SimilarRunResponse",
]
