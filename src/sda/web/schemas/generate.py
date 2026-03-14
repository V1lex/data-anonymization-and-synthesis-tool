from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_ROWS_PER_FILE = 10_000
MIN_ROWS_PER_FILE = 1
MAX_TEMPLATE_COLUMNS = 64
VALID_TEMPLATE_IDS = {
    "users",
    "orders",
    "payments",
    "products",
    "support_tickets",
}


class GenerateTemplateId(str, Enum):
    USERS = "users"
    ORDERS = "orders"
    PAYMENTS = "payments"
    PRODUCTS = "products"
    SUPPORT_TICKETS = "support_tickets"


class ResultFormat(str, Enum):
    CSV_BASE64 = "csv_base64"
    ZIP_BASE64 = "zip_base64"


class ErrorResponse(BaseModel):
    error_code: str = Field(..., examples=["validation_error"])
    message: str = Field(..., min_length=1, examples=["row_count must be between 1 and 10000"])
    details: dict[str, Any] | None = Field(default=None)
    request_id: str | None = Field(default=None)


class GenerateTemplateColumn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1, max_length=256)
    example_value: str | None = Field(default=None, max_length=256)
    pii_expected: bool = Field(default=False)

    @field_validator("name")
    @classmethod
    def validate_column_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("column name must not be blank")
        if any(char in normalized for char in "\r\n\t"):
            raise ValueError("column name must not contain control characters")
        return normalized


class GenerateTemplateSummary(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    template_id: GenerateTemplateId
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1, max_length=512)
    columns: list[str] = Field(..., min_length=1, max_length=MAX_TEMPLATE_COLUMNS)
    default_rows: int = Field(default=100, ge=MIN_ROWS_PER_FILE, le=MAX_ROWS_PER_FILE)
    max_rows: int = Field(default=MAX_ROWS_PER_FILE, ge=MIN_ROWS_PER_FILE, le=MAX_ROWS_PER_FILE)

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for column in value:
            name = column.strip()
            if not name:
                raise ValueError("column names must not be blank")
            if any(char in name for char in "\r\n\t"):
                raise ValueError("column names must not contain control characters")
            normalized.append(name)
        if len(set(normalized)) != len(normalized):
            raise ValueError("column names must be unique")
        return normalized


class GenerateTemplateDetail(GenerateTemplateSummary):
    recommended_rows: list[int] = Field(default_factory=lambda: [100, 500, 1_000, 5_000])
    relations: list[str] = Field(default_factory=list)
    columns_detail: list[GenerateTemplateColumn] = Field(..., min_length=1, max_length=MAX_TEMPLATE_COLUMNS)

    @field_validator("recommended_rows")
    @classmethod
    def validate_recommended_rows(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("recommended_rows must not be empty")
        if sorted(set(value)) != value:
            raise ValueError("recommended_rows must be unique and sorted ascending")
        for row_count in value:
            if row_count < MIN_ROWS_PER_FILE or row_count > MAX_ROWS_PER_FILE:
                raise ValueError("recommended_rows values must be between 1 and 10000")
        return value


class GenerateRunItem(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    template_id: GenerateTemplateId
    row_count: int = Field(..., ge=MIN_ROWS_PER_FILE, le=MAX_ROWS_PER_FILE)
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


class GenerateRunRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    items: list[GenerateRunItem] = Field(..., min_length=1, max_length=len(VALID_TEMPLATE_IDS))
    result_format: ResultFormat = Field(default=ResultFormat.ZIP_BASE64)
    random_seed: int | None = Field(default=None, ge=0, le=2_147_483_647)

    @model_validator(mode="after")
    def validate_items(self) -> "GenerateRunRequest":
        template_ids = [item.template_id for item in self.items]
        if len(set(template_ids)) != len(template_ids):
            raise ValueError("each template_id can be requested only once")
        if self.result_format == ResultFormat.CSV_BASE64 and len(self.items) != 1:
            raise ValueError("result_format=csv_base64 requires exactly one requested template")
        return self


class GeneratedFile(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    template_id: GenerateTemplateId
    file_name: str = Field(..., min_length=1, max_length=128)
    row_count: int = Field(..., ge=MIN_ROWS_PER_FILE, le=MAX_ROWS_PER_FILE)
    content_base64: str = Field(..., min_length=1)
    content_type: str = Field(default="text/csv")


class GenerateRunResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    result_format: ResultFormat
    file_name: str = Field(..., min_length=1, max_length=128)
    generated_files: list[GeneratedFile] = Field(..., min_length=1, max_length=len(VALID_TEMPLATE_IDS))
    archive_base64: str | None = Field(default=None, min_length=1)
    total_rows: int = Field(..., ge=MIN_ROWS_PER_FILE, le=MAX_ROWS_PER_FILE * len(VALID_TEMPLATE_IDS))
    warnings: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "GenerateRunResponse":
        if self.result_format == ResultFormat.ZIP_BASE64 and not self.archive_base64:
            raise ValueError("archive_base64 is required for zip_base64 responses")
        if self.result_format == ResultFormat.CSV_BASE64 and len(self.generated_files) != 1:
            raise ValueError("csv_base64 responses must contain exactly one generated file")
        return self


__all__ = [
    "ErrorResponse",
    "GeneratedFile",
    "GenerateRunItem",
    "GenerateRunRequest",
    "GenerateRunResponse",
    "GenerateTemplateColumn",
    "GenerateTemplateDetail",
    "GenerateTemplateId",
    "GenerateTemplateSummary",
    "ResultFormat",
]
