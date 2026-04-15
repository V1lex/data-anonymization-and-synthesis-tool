import io
import zipfile
from collections.abc import Sequence
from typing import Any

from sda.core.domain.errors import GenerationError
from sda.core.generation.validators import apply_generation_semantics
from sda.core.generation.generator import DEFAULT_FAKER_LOCALE, DataGenerator
from sda.io.csv_write import write_csv_bytes

TEMPLATE_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "users": (),
    "orders": ("users", "products"),
    "payments": ("users", "orders"),
    "products": (),
    "support_tickets": ("users",),
}


def _zip_generated_files(files: Sequence[dict[str, Any]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.writestr(item["file_name"], item["content"])
    return buffer.getvalue()


def _validate_dependencies(items: Sequence[dict[str, int]]) -> None:
    requested_template_ids = {str(item.get("template_id")) for item in items}
    for item in items:
        template_id = str(item.get("template_id"))
        missing_dependencies = [
            dependency
            for dependency in TEMPLATE_DEPENDENCIES.get(template_id, ())
            if dependency not in requested_template_ids
        ]
        if missing_dependencies:
            raise GenerationError(
                f"Для генерации '{template_id}' нужно также выбрать: {', '.join(missing_dependencies)}.",
                details={
                    "template_id": template_id,
                    "missing_dependencies": missing_dependencies,
                },
            )


def _order_generation_items(items: list[dict[str, int]]) -> list[dict[str, int]]:
    items_by_template_id = {
        str(item["template_id"]): item
        for item in items
    }
    ordered_items: list[dict[str, int]] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(template_id: str) -> None:
        if template_id in visited:
            return
        if template_id in visiting:
            raise GenerationError(
                "Обнаружен цикл зависимостей между шаблонами генерации.",
                details={"template_id": template_id},
            )

        visiting.add(template_id)
        for dependency in TEMPLATE_DEPENDENCIES.get(template_id, ()):
            if dependency in items_by_template_id:
                visit(dependency)
        visiting.remove(template_id)
        visited.add(template_id)
        ordered_items.append(items_by_template_id[template_id])

    for item in items:
        visit(str(item["template_id"]))

    return ordered_items


def generate_csv_use_case(
    items: list[dict[str, int]],
    *,
    delimiter: str = ",",
    locale: str = DEFAULT_FAKER_LOCALE,
    generator: DataGenerator | None = None,
) -> dict[str, Any]:
    """Use case генерации CSV на уровне приложения.

    Пример входа:
    [
      {"template_id": "users", "row_count": 100},
      {"template_id": "orders", "row_count": 100}
    ]

    Возвращаемая структура готова для сериализации в `web/routers/generate.py`.
    """
    if not items:
        raise GenerationError("Нужно передать хотя бы один элемент генерации.")

    seen: set[str] = set()
    for item in items:
        template_id = item.get("template_id")
        if template_id in seen:
            raise GenerationError(f"Повторяющийся template_id в запросе: '{template_id}'")
        seen.add(template_id)

    _validate_dependencies(items)
    ordered_items = _order_generation_items(items)

    data_generator = generator or DataGenerator(locale=locale)
    set_locale = getattr(data_generator, "set_locale", None)
    if callable(set_locale):
        set_locale(locale)
    tables = data_generator.generate_tables(ordered_items)
    tables = apply_generation_semantics(tables, locale=locale)

    generated_files: list[dict[str, Any]] = []
    total_rows = 0
    for item in ordered_items:
        template_id = item["template_id"]
        rows = tables[template_id]
        csv_content = write_csv_bytes(rows, delimiter=delimiter)
        generated_files.append(
            {
                "template_id": template_id,
                "file_name": f"{template_id}.csv",
                "row_count": len(rows),
                "content_type": "text/csv",
                "content": csv_content,
            }
        )
        total_rows += len(rows)

    if len(generated_files) == 1:
        single = generated_files[0]
        return {
            "result_format": "single_csv",
            "file_name": single["file_name"],
            "total_rows": total_rows,
            "generated_files": generated_files,
            "content": single["content"],
            "archive_content": None,
        }

    archive = _zip_generated_files(generated_files)
    return {
        "result_format": "zip_archive",
        "file_name": "generated_bundle.zip",
        "total_rows": total_rows,
        "generated_files": generated_files,
        "content": None,
        "archive_content": archive,
    }
