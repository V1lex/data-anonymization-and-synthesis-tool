import json
from pathlib import Path
from random import choice
from uuid import uuid4

from faker import Faker

from sda.core.domain.errors import GenerationError


class DataGenerator:
    def __init__(self) -> None:
        self.faker = Faker()
        self.templates_dir = Path(__file__).resolve().parents[2] / "resources" / "templates"
        self.context: dict[str, list[dict[str, object]]] = {
            "users": [],
            "orders": [],
            "payments": [],
            "products": [],
            "support_tickets": [],
        }

    def load_template(self, template_id: str) -> dict:
        path = self.templates_dir / f"{template_id}.json"
        if not path.exists():
            raise GenerationError(f"Шаблон '{template_id}' не найден: {path}")

        with path.open("r", encoding="utf-8") as file:
            template = json.load(file)

        if not isinstance(template, dict):
            raise GenerationError(f"Шаблон '{template_id}' должен быть JSON-объектом")

        columns = template.get("columns")
        if not isinstance(columns, list) or not columns:
            raise GenerationError(
                f"Шаблон '{template_id}' должен содержать непустой список 'columns'"
            )

        return template

    def generate_table(self, template_id: str, count: int) -> list[dict[str, object]]:
        if count <= 0:
            raise GenerationError("Количество строк для генерации должно быть больше нуля")

        if template_id not in self.context:
            raise GenerationError(f"Неподдерживаемый template_id: '{template_id}'")

        template = self.load_template(template_id)
        rows: list[dict[str, object]] = []

        for _ in range(count):
            row = self._generate_row(template_id, template)
            rows.append(row)
            self.context[template_id].append(row)

        return rows

    def reset_context(self) -> None:
        """Reset in-memory context between generation sessions."""
        for key in self.context:
            self.context[key] = []

    def generate_tables(self, items: list[dict[str, int]]) -> dict[str, list[dict[str, object]]]:
        """
        Generate multiple tables in request order.

        Each item must contain:
        - template_id: str
        - row_count: int
        """
        if not items:
            raise GenerationError("Generation items list cannot be empty.")

        self.reset_context()
        result: dict[str, list[dict[str, object]]] = {}

        for item in items:
            template_id = item.get("template_id")
            row_count = item.get("row_count")

            if not isinstance(template_id, str) or not template_id:
                raise GenerationError("Each item must include non-empty template_id.")
            if not isinstance(row_count, int):
                raise GenerationError(f"row_count for '{template_id}' must be integer.")

            result[template_id] = self.generate_table(template_id=template_id, count=row_count)

        return result

    def _generate_row(self, template_id: str, template: dict) -> dict[str, object]:
        # Специальный случай: для payments нужно согласовать order_id и user_id
        if template_id == "payments":
            return self._generate_payment_row(template)

        row: dict[str, object] = {}

        for column in template["columns"]:
            self._validate_column_config(template_id, column)
            value = self._generate_column_value(template_id=template_id, column=column)
            row[column["name"]] = value

        return row

    def _generate_payment_row(self, template: dict) -> dict[str, object]:
        if not self.context["orders"]:
            raise GenerationError("Нельзя сгенерировать payments без ранее созданных orders")

        selected_order = choice(self.context["orders"])
        row: dict[str, object] = {}

        for column in template["columns"]:
            self._validate_column_config("payments", column)
            column_name = column["name"]

            if column_name == "order_id":
                row[column_name] = selected_order["order_id"]
                continue

            if column_name == "user_id":
                row[column_name] = selected_order["user_id"]
                continue

            row[column_name] = self._generate_column_value(
                template_id="payments",
                column=column,
            )

        return row

    def _generate_column_value(self, template_id: str, column: dict) -> object:
        provider = column["provider"]

        if provider == "uuid4":
            return str(uuid4())

        if provider == "random_int":
            min_value = column.get("min", 0)
            max_value = column.get("max", 100)

            if min_value > max_value:
                raise GenerationError(
                    f"Колонка '{column['name']}' в шаблоне '{template_id}' "
                    f"имеет некорректный диапазон random_int: min={min_value}, max={max_value}"
                )

            return self.faker.random_int(min=min_value, max=max_value)

        if provider == "random_element":
            elements = column.get("elements")
            if not isinstance(elements, list) or not elements:
                raise GenerationError(
                    f"Колонка '{column['name']}' в шаблоне '{template_id}' "
                    "использует random_element без непустого списка 'elements'"
                )
            return self.faker.random_element(elements)

        if provider == "context_ref":
            return self._resolve_context_ref(template_id=template_id, column=column)

        if provider == "date_time_between":
            start_date = column.get("start_date", "-2y")
            end_date = column.get("end_date", "now")
            return self.faker.date_time_between(
                start_date=start_date,
                end_date=end_date,
            ).isoformat()

        if provider == "date_of_birth":
            minimum_age = column.get("minimum_age", 18)
            maximum_age = column.get("maximum_age", 90)
            return self.faker.date_of_birth(
                minimum_age=minimum_age,
                maximum_age=maximum_age,
            ).isoformat()

        if provider == "boolean":
            return self.faker.boolean()

        faker_method = getattr(self.faker, provider, None)
        if faker_method is None or not callable(faker_method):
            raise GenerationError(
                f"Неподдерживаемый provider '{provider}' "
                f"для колонки '{column['name']}' в шаблоне '{template_id}'"
            )

        return faker_method()

    def _resolve_context_ref(self, template_id: str, column: dict) -> object:
        ref = column.get("ref")
        if not ref:
            raise GenerationError(
                f"Колонка '{column['name']}' в шаблоне '{template_id}' "
                "использует context_ref без поля 'ref'"
            )

        if ref == "user_id":
            if not self.context["users"]:
                raise GenerationError(
                    f"Нельзя сгенерировать '{template_id}', потому что контекст users пуст"
                )
            selected_user = choice(self.context["users"])
            return selected_user["user_id"]

        if ref == "order_id":
            if not self.context["orders"]:
                raise GenerationError(
                    f"Нельзя сгенерировать '{template_id}', потому что контекст orders пуст"
                )
            selected_order = choice(self.context["orders"])
            return selected_order["order_id"]

        raise GenerationError(
            f"Неподдерживаемая ссылка на контекст '{ref}' "
            f"для колонки '{column['name']}' в шаблоне '{template_id}'"
        )

    def _validate_column_config(self, template_id: str, column: dict) -> None:
        if not isinstance(column, dict):
            raise GenerationError(
                f"Каждая колонка в шаблоне '{template_id}' должна быть JSON-объектом"
            )

        name = column.get("name")
        provider = column.get("provider")

        if not isinstance(name, str) or not name.strip():
            raise GenerationError(
                f"Шаблон '{template_id}' содержит колонку с некорректным полем 'name'"
            )

        if not isinstance(provider, str) or not provider.strip():
            raise GenerationError(
                f"Колонка '{name}' в шаблоне '{template_id}' "
                "должна содержать непустое поле 'provider'"
            )
