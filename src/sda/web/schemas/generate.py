from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sda.core.generation.validators import VALID_GENERATION_DOMAINS
from sda.core.generation.generator import DEFAULT_FAKER_LOCALE

MAX_ROWS_PER_FILE = 10_000
MIN_ROWS_PER_FILE = 1
MAX_TEMPLATE_COLUMNS = 64
MAX_PREVIEW_COLUMNS = MAX_TEMPLATE_COLUMNS
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


class FakerLocale(str, Enum):
    RU_RU = "ru_RU"
    EN_US = "en_US"


class GenerateDomainId(str, Enum):
    ECOMMERCE = "ecommerce"
    FINTECH = "fintech"
    SHOPS = "shops"
    LOGISTICS = "logistics"
    EDUCATION = "education"
    CRM = "crm"


class GenerateDomainSummary(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    domain_id: GenerateDomainId
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1, max_length=512)


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(..., examples=["validation_error"])
    message: str = Field(..., min_length=1, examples=["row_count must be between 1 and 10000"])
    details: dict[str, Any] | None = Field(default=None)
    request_id: str | None = Field(default=None)


class GenerateTemplateColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    template_id: GenerateTemplateId
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, min_length=1, max_length=512)
    preview_columns: list[str] | None = Field(default=None, min_length=1, max_length=MAX_PREVIEW_COLUMNS)
    
    @field_validator("preview_columns")
    @classmethod
    def validate_preview_columns(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
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
    columns: list[GenerateTemplateColumn] = Field(..., min_length=1, max_length=MAX_TEMPLATE_COLUMNS)


class GenerateRunItem(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    template_id: GenerateTemplateId
    row_count: int = Field(..., ge=MIN_ROWS_PER_FILE, le=MAX_ROWS_PER_FILE)


class GenerateRunRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    items: list[GenerateRunItem] = Field(..., min_length=1, max_length=len(VALID_TEMPLATE_IDS))
    locale: FakerLocale = Field(default=DEFAULT_FAKER_LOCALE)
    domain: GenerateDomainId = Field(default=GenerateDomainId.ECOMMERCE)

    @model_validator(mode="after")
    def validate_items(self) -> "GenerateRunRequest":
        template_ids = [item.template_id for item in self.items]
        if len(set(template_ids)) != len(template_ids):
            raise ValueError("each template_id can be requested only once")
        if self.domain not in VALID_GENERATION_DOMAINS:
            raise ValueError("domain is not supported")
        return self


class GeneratedFile(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    template_id: GenerateTemplateId
    file_name: str = Field(..., min_length=1, max_length=128)
    row_count: int = Field(..., ge=MIN_ROWS_PER_FILE, le=MAX_ROWS_PER_FILE)
    content_type: str = Field(default="text/csv")


class GenerateRunResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    result_format: ResultFormat
    file_name: str = Field(..., min_length=1, max_length=128)
    generated_files: list[GeneratedFile] = Field(..., min_length=1, max_length=len(VALID_TEMPLATE_IDS))
    content_base64: str | None = Field(default=None, min_length=1)
    archive_base64: str | None = Field(default=None, min_length=1)
    total_rows: int = Field(..., ge=MIN_ROWS_PER_FILE, le=MAX_ROWS_PER_FILE * len(VALID_TEMPLATE_IDS))
    warnings: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_payload_shape(self) -> "GenerateRunResponse":
        if self.result_format == ResultFormat.ZIP_BASE64:
            if len(self.generated_files) < 2:
                raise ValueError("zip_base64 responses must describe at least two generated files")
            if not self.archive_base64:
                raise ValueError("archive_base64 is required for zip_base64 responses")
            if self.content_base64 is not None:
                raise ValueError("content_base64 must be omitted for zip_base64 responses")
        if self.result_format == ResultFormat.CSV_BASE64:
            if len(self.generated_files) != 1:
                raise ValueError("csv_base64 responses must contain exactly one generated file")
            if not self.content_base64:
                raise ValueError("content_base64 is required for csv_base64 responses")
            if self.archive_base64 is not None:
                raise ValueError("archive_base64 must be omitted for csv_base64 responses")
        return self


__all__ = [
    "ErrorResponse",
    "FakerLocale",
    "GenerateDomainId",
    "GenerateDomainSummary",
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
