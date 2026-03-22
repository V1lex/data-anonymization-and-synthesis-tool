import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from uuid import uuid4

from sda.core.domain.errors import TemplateNotFoundError, UploadNotFoundError

TEMPLATE_DESCRIPTIONS = {
    "users": "Синтетические профили пользователей для демонстрационных наборов данных.",
    "orders": "Синтетическая история заказов, связанная с пользователями.",
    "payments": "Синтетические платежные операции, связанные с заказами.",
    "products": "Синтетический каталог товаров.",
    "support_tickets": "Синтетические обращения в поддержку.",
}


def _templates_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "templates"


def load_template_payload(template_id: str) -> dict:
    path = _templates_dir() / f"{template_id}.json"
    if not path.exists():
        raise TemplateNotFoundError(f"Шаблон '{template_id}' не найден.")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_template_catalog() -> list[dict]:
    items: list[dict] = []
    for path in sorted(_templates_dir().glob("*.json")):
        payload = load_template_payload(path.stem)
        columns = payload.get("columns", [])
        items.append(
            {
                "template_id": payload["template_id"],
                "name": payload.get("title", payload["template_id"].replace("_", " ").title()),
                "description": TEMPLATE_DESCRIPTIONS.get(payload["template_id"]),
                "preview_columns": [column["name"] for column in columns[:4]],
                "columns": columns,
            }
        )
    return items


def describe_column(column_name: str) -> str:
    return column_name.replace("_", " ").strip().capitalize()


@dataclass
class UploadedCsvSession:
    upload_id: str
    file_name: str
    rows: list[dict[str, str]]
    header: list[str]
    delimiter: str
    encoding: str = "utf-8"


class UploadStore:
    def __init__(self) -> None:
        self._items: dict[str, UploadedCsvSession] = {}
        self._lock = Lock()

    def create(
        self,
        *,
        file_name: str,
        rows: list[dict[str, str]],
        header: list[str],
        delimiter: str,
        encoding: str = "utf-8",
    ) -> UploadedCsvSession:
        session = UploadedCsvSession(
            upload_id=f"upl_{uuid4().hex[:12]}",
            file_name=file_name,
            rows=rows,
            header=header,
            delimiter=delimiter,
            encoding=encoding,
        )
        with self._lock:
            self._items[session.upload_id] = session
        return session

    def get(self, upload_id: str) -> UploadedCsvSession:
        with self._lock:
            session = self._items.get(upload_id)
        if session is None:
            raise UploadNotFoundError(f"upload_id '{upload_id}' не найден.")
        return session


_upload_store = UploadStore()


def get_upload_store() -> UploadStore:
    return _upload_store
