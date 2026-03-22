import base64

from fastapi import APIRouter

from sda.use_cases.generate_csv import generate_csv_use_case
from sda.web.deps import TEMPLATE_DESCRIPTIONS, describe_column, load_template_catalog, load_template_payload
from sda.web.schemas.generate import (
    GenerateRunRequest,
    GenerateRunResponse,
    GeneratedFile,
    GenerateTemplateColumn,
    GenerateTemplateDetail,
    GenerateTemplateSummary,
    ResultFormat,
)

router = APIRouter(prefix="/generate", tags=["generate"])


def _build_generated_file(item: dict) -> GeneratedFile:
    return GeneratedFile(
        template_id=item["template_id"],
        file_name=item["file_name"],
        row_count=item["row_count"],
        content_type=item["content_type"],
    )


@router.get("/templates")
def get_templates() -> dict[str, list[dict]]:
    items = [
        GenerateTemplateSummary(
            template_id=item["template_id"],
            name=item["name"],
            description=item["description"],
            preview_columns=item["preview_columns"],
        ).model_dump()
        for item in load_template_catalog()
    ]
    return {"items": items}


@router.get("/templates/{template_id}")
def get_template_detail(template_id: str) -> dict:
    payload = load_template_payload(template_id)
    columns = payload.get("columns", [])
    detail = GenerateTemplateDetail(
        template_id=payload["template_id"],
        name=payload.get("title", payload["template_id"].replace("_", " ").title()),
        description=TEMPLATE_DESCRIPTIONS.get(payload["template_id"]),
        preview_columns=[column["name"] for column in columns[:4]],
        columns=[
            GenerateTemplateColumn(
                name=column["name"],
                description=describe_column(column["name"]),
                example_value=None,
                pii_expected=column["name"] in {"full_name", "email", "phone", "address", "birth_date"},
            )
            for column in columns
        ],
    )
    return detail.model_dump()


@router.post("/run")
def run_generate(request: GenerateRunRequest) -> dict:
    result = generate_csv_use_case([item.model_dump() for item in request.items])
    generated_files = [_build_generated_file(item).model_dump() for item in result["generated_files"]]

    if result["content"] is not None:
        response = GenerateRunResponse(
            result_format=ResultFormat.CSV_BASE64,
            file_name=result["file_name"],
            generated_files=generated_files,
            content_base64=base64.b64encode(result["content"]).decode("ascii"),
            archive_base64=None,
            total_rows=result["total_rows"],
            warnings=[],
        )
    else:
        response = GenerateRunResponse(
            result_format=ResultFormat.ZIP_BASE64,
            file_name=result["file_name"],
            generated_files=generated_files,
            content_base64=None,
            archive_base64=base64.b64encode(result["archive_content"]).decode("ascii"),
            total_rows=result["total_rows"],
            warnings=[],
        )

    return response.model_dump()
