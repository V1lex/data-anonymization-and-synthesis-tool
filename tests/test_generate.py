import io
import zipfile

import pytest

from sda.core.domain.errors import GenerationError
from sda.use_cases.generate_csv import generate_csv_use_case


class StubGenerator:
    def __init__(self) -> None:
        self.received_items: list[dict[str, int]] = []

    def generate_tables(self, items: list[dict[str, int]]) -> dict[str, list[dict[str, object]]]:
        self.received_items = items
        return {
            item["template_id"]: [
                {"id": f'{item["template_id"]}-{index + 1}', "value": str(index + 1)}
                for index in range(item["row_count"])
            ]
            for item in items
        }


def test_generate_csv_use_case_returns_single_csv_payload() -> None:
    result = generate_csv_use_case(
        [{"template_id": "users", "row_count": 2}],
        generator=StubGenerator(),
    )

    assert result["result_format"] == "single_csv"
    assert result["file_name"] == "users.csv"
    assert result["archive_content"] is None
    assert result["total_rows"] == 2
    assert result["generated_files"][0]["row_count"] == 2
    assert result["content"].decode("utf-8") == "id,value\nusers-1,1\nusers-2,2\n"


def test_generate_csv_use_case_returns_zip_for_multiple_tables() -> None:
    result = generate_csv_use_case(
        [
            {"template_id": "users", "row_count": 1},
            {"template_id": "products", "row_count": 1},
        ],
        generator=StubGenerator(),
    )

    assert result["result_format"] == "zip_archive"
    assert result["file_name"] == "generated_bundle.zip"
    assert result["content"] is None
    assert result["total_rows"] == 2

    archive = zipfile.ZipFile(io.BytesIO(result["archive_content"]))
    assert sorted(archive.namelist()) == ["products.csv", "users.csv"]


def test_generate_csv_use_case_rejects_duplicate_template_ids() -> None:
    with pytest.raises(GenerationError):
        generate_csv_use_case(
            [
                {"template_id": "users", "row_count": 1},
                {"template_id": "users", "row_count": 2},
            ],
            generator=StubGenerator(),
        )


def test_generate_csv_use_case_orders_items_by_dependencies() -> None:
    generator = StubGenerator()

    generate_csv_use_case(
        [
            {"template_id": "orders", "row_count": 2},
            {"template_id": "users", "row_count": 2},
            {"template_id": "payments", "row_count": 2},
        ],
        generator=generator,
    )

    assert [item["template_id"] for item in generator.received_items] == ["users", "orders", "payments"]


def test_generate_csv_use_case_rejects_missing_dependencies() -> None:
    with pytest.raises(GenerationError, match="Для генерации 'orders' нужно также выбрать: users."):
        generate_csv_use_case(
            [{"template_id": "orders", "row_count": 1}],
            generator=StubGenerator(),
        )
