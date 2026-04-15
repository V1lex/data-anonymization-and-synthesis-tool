from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sda.core.anonymization.rules import AnonymizationMethod
from sda.core.domain.limits import MAX_CSV_COLUMNS, MAX_CSV_ROWS
from sda.web.schemas.generate import ErrorResponse, ResultFormat

MAX_SAMPLE_VALUES = 5


def _normalize_column_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("column_name must not be blank")
    if any(char in normalized for char in "\r\n\t"):
        raise ValueError("column_name must not contain control characters")
    return normalized


class UploadedCsvColumn(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    index: int = Field(..., ge=0, le=MAX_CSV_COLUMNS - 1)
    name: str = Field(..., min_length=1, max_length=128)
    inferred_type: str = Field(..., min_length=1, max_length=32)
    detected_type: str = Field(..., min_length=1, max_length=32)
    sample_values: list[str] = Field(default_factory=list, max_length=MAX_SAMPLE_VALUES)
    null_ratio: float = Field(..., ge=0.0, le=1.0)
    unique_ratio: float = Field(..., ge=0.0, le=1.0)
    reason: str | None = Field(default=None, max_length=256)
    suggested_method: AnonymizationMethod | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    hint: str | None = Field(default=None, max_length=256)
    unsupported_methods: dict[str, str] = Field(default_factory=dict, max_length=5)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _normalize_column_name(value)

    @field_validator("sample_values")
    @classmethod
    def validate_sample_values(cls, value: list[str]) -> list[str]:
        return [sample.strip() for sample in value]

    @field_validator("unsupported_methods")
    @classmethod
    def validate_unsupported_methods(cls, value: dict[str, str]) -> dict[str, str]:
        return {
            str(method).strip(): str(message).strip()
            for method, message in value.items()
            if str(method).strip() and str(message).strip()
        }


class AnonymizationRule(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    column_name: str = Field(..., min_length=1, max_length=128)
    method: AnonymizationMethod
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("column_name")
    @classmethod
    def validate_column_name(cls, value: str) -> str:
        return _normalize_column_name(value)


class AnonymizeUploadResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    upload_id: str = Field(..., min_length=1, max_length=64)
    file_name: str = Field(..., min_length=1, max_length=256)
    row_count: int = Field(..., ge=1, le=MAX_CSV_ROWS)
    column_count: int = Field(..., ge=1, le=MAX_CSV_COLUMNS)
    columns: list[UploadedCsvColumn] = Field(..., min_length=1, max_length=MAX_CSV_COLUMNS)
    preview_rows: list[dict[str, str | None]] = Field(default_factory=list, max_length=5)
    delimiter: str = Field(default=",", min_length=1, max_length=1)
    encoding: str = Field(default="utf-8", min_length=3, max_length=32)
    warnings: list[str] = Field(default_factory=list, max_length=10)


class AnonymizeRunRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    upload_id: str = Field(..., min_length=1, max_length=64)
    rules: list[AnonymizationRule] = Field(..., min_length=1, max_length=MAX_CSV_COLUMNS)

    @model_validator(mode="after")
    def validate_unique_columns(self) -> "AnonymizeRunRequest":
        column_names = [rule.column_name for rule in self.rules]
        if len(set(column_names)) != len(column_names):
            raise ValueError("rules must reference each column at most once")
        return self


class AnonymizeRunResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    upload_id: str = Field(..., min_length=1, max_length=64)
    file_name: str = Field(..., min_length=1, max_length=128)
    row_count: int = Field(..., ge=1, le=MAX_CSV_ROWS)
    column_count: int = Field(..., ge=1, le=MAX_CSV_COLUMNS)
    result_format: ResultFormat = Field(default=ResultFormat.CSV_BASE64)
    content_base64: str = Field(..., min_length=1)
    applied_rules: list[AnonymizationRule] = Field(..., min_length=1, max_length=MAX_CSV_COLUMNS)
    warnings: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_result_format(self) -> "AnonymizeRunResponse":
        if self.result_format != ResultFormat.CSV_BASE64:
            raise ValueError("anonymize responses support only csv_base64")
        return self


__all__ = [
    "AnonymizationMethod",
    "AnonymizationRule",
    "AnonymizeRunRequest",
    "AnonymizeRunResponse",
    "AnonymizeUploadResponse",
    "ErrorResponse",
    "ResultFormat",
    "UploadedCsvColumn",
]
