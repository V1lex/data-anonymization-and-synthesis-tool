from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sda.web.schemas.generate import ErrorResponse, ResultFormat

MAX_SIMILAR_ROWS = 10_000
MAX_SIMILAR_COLUMNS = 128


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


__all__ = [
    "ErrorResponse",
    "ResultFormat",
    "SimilarAnalyzeRequest",
    "SimilarAnalyzeResponse",
    "SimilarColumnProfile",
    "SimilarRunRequest",
    "SimilarRunResponse",
]
