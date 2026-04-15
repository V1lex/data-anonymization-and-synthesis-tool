import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import gettempdir
from threading import Lock
from typing import Any

from sda.core.domain.limits import UPLOAD_TTL_SECONDS
from sda.core.domain.errors import AnalysisNotFoundError, TemplateNotFoundError, UploadNotFoundError

TEMPLATE_DESCRIPTIONS = {
    "users": "Синтетические профили пользователей для демонстрационных наборов данных.",
    "orders": "Синтетическая история заказов, связанная с пользователями и товарами.",
    "payments": "Синтетические платежные операции, связанные с заказами.",
    "products": "Синтетический каталог товаров.",
    "support_tickets": "Синтетические обращения в поддержку.",
}
TEMPLATE_DISPLAY_ORDER = (
    "users",
    "orders",
    "payments",
    "products",
    "support_tickets",
)
UPLOAD_STORE_DIR = Path(gettempdir()) / "sda_upload_store"
UPLOAD_ID_PREFIX = "upload_"
SIMILAR_ANALYSIS_STORE_DIR = Path(gettempdir()) / "sda_similar_analysis_store"
ANALYSIS_ID_PREFIX = "ana_"


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
    for path in _templates_dir().glob("*.json"):
        payload = load_template_payload(path.stem)
        columns = payload.get("columns", [])
        items.append(
            {
                "template_id": payload["template_id"],
                "name": payload.get("title", payload["template_id"].replace("_", " ").title()),
                "description": TEMPLATE_DESCRIPTIONS.get(payload["template_id"]),
                "preview_columns": [column["name"] for column in columns],
                "columns": columns,
            }
        )
    order_index = {template_id: index for index, template_id in enumerate(TEMPLATE_DISPLAY_ORDER)}
    items.sort(key=lambda item: order_index.get(item["template_id"], len(order_index)))
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
    created_at: float = field(default_factory=time.time)


@dataclass
class SimilarAnalysisSession:
    analysis_id: str
    file_name: str
    rows: list[dict[str, str]]
    header: list[str]
    delimiter: str
    metadata: dict[str, Any]
    column_specs: dict[str, dict[str, Any]]
    encoding: str = "utf-8"
    created_at: float = field(default_factory=time.time)


class UploadStore:
    def __init__(self, *, storage_dir: Path | None = None, ttl_seconds: int = UPLOAD_TTL_SECONDS) -> None:
        self._storage_dir = Path(storage_dir or UPLOAD_STORE_DIR)
        self._ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, upload_id: str) -> Path:
        return self._storage_dir / f"{upload_id}.json"

    def _write_session(self, session: UploadedCsvSession) -> None:
        path = self._session_path(session.upload_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(asdict(session), ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)

    def _read_session(self, upload_id: str) -> UploadedCsvSession:
        path = self._session_path(upload_id)
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return UploadedCsvSession(
            upload_id=str(payload["upload_id"]),
            file_name=str(payload["file_name"]),
            rows=list(payload["rows"]),
            header=list(payload["header"]),
            delimiter=str(payload["delimiter"]),
            encoding=str(payload.get("encoding", "utf-8")),
            created_at=float(payload.get("created_at", 0.0)),
        )

    def _is_expired(self, session: UploadedCsvSession) -> bool:
        return self._ttl_seconds > 0 and (time.time() - session.created_at) > self._ttl_seconds

    def _cleanup_expired_locked(self) -> None:
        for path in self._storage_dir.glob("*.json"):
            try:
                session = self._read_session(path.stem)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                path.unlink(missing_ok=True)
                continue

            if self._is_expired(session):
                path.unlink(missing_ok=True)

    def _next_upload_id_locked(self) -> str:
        next_value = 1
        for path in self._storage_dir.glob(f"{UPLOAD_ID_PREFIX}*.json"):
            suffix = path.stem.removeprefix(UPLOAD_ID_PREFIX)
            if suffix.isdigit():
                next_value = max(next_value, int(suffix) + 1)
        return f"{UPLOAD_ID_PREFIX}{next_value}"

    def create(
        self,
        *,
        file_name: str,
        rows: list[dict[str, str]],
        header: list[str],
        delimiter: str,
        encoding: str = "utf-8",
    ) -> UploadedCsvSession:
        with self._lock:
            self._cleanup_expired_locked()
            session = UploadedCsvSession(
                upload_id=self._next_upload_id_locked(),
                file_name=file_name,
                rows=rows,
                header=header,
                delimiter=delimiter,
                encoding=encoding,
            )
            self._write_session(session)
        return session

    def get(self, upload_id: str) -> UploadedCsvSession:
        with self._lock:
            path = self._session_path(upload_id)
            if not path.exists():
                raise UploadNotFoundError(
                    f"upload_id '{upload_id}' не найден.",
                    details={"upload_id": upload_id},
                )
            session = self._read_session(upload_id)
            if self._is_expired(session):
                path.unlink(missing_ok=True)
                raise UploadNotFoundError(
                    f"upload_id '{upload_id}' истек.",
                    details={"upload_id": upload_id},
                )
        return session


class SimilarAnalysisStore:
    def __init__(self, *, storage_dir: Path | None = None, ttl_seconds: int = UPLOAD_TTL_SECONDS) -> None:
        self._storage_dir = Path(storage_dir or SIMILAR_ANALYSIS_STORE_DIR)
        self._ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, analysis_id: str) -> Path:
        return self._storage_dir / f"{analysis_id}.json"

    def _write_session(self, session: SimilarAnalysisSession) -> None:
        path = self._session_path(session.analysis_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(asdict(session), ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)

    def _read_session(self, analysis_id: str) -> SimilarAnalysisSession:
        path = self._session_path(analysis_id)
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return SimilarAnalysisSession(
            analysis_id=str(payload["analysis_id"]),
            file_name=str(payload["file_name"]),
            rows=list(payload["rows"]),
            header=list(payload["header"]),
            delimiter=str(payload["delimiter"]),
            metadata=dict(payload["metadata"]),
            column_specs=dict(payload["column_specs"]),
            encoding=str(payload.get("encoding", "utf-8")),
            created_at=float(payload.get("created_at", 0.0)),
        )

    def _is_expired(self, session: SimilarAnalysisSession) -> bool:
        return self._ttl_seconds > 0 and (time.time() - session.created_at) > self._ttl_seconds

    def _cleanup_expired_locked(self) -> None:
        for path in self._storage_dir.glob("*.json"):
            try:
                session = self._read_session(path.stem)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                path.unlink(missing_ok=True)
                continue

            if self._is_expired(session):
                path.unlink(missing_ok=True)

    def _next_analysis_id_locked(self) -> str:
        next_value = 1
        for path in self._storage_dir.glob(f"{ANALYSIS_ID_PREFIX}*.json"):
            suffix = path.stem.removeprefix(ANALYSIS_ID_PREFIX)
            if suffix.isdigit():
                next_value = max(next_value, int(suffix) + 1)
        return f"{ANALYSIS_ID_PREFIX}{next_value}"

    def create(
        self,
        *,
        file_name: str,
        rows: list[dict[str, str]],
        header: list[str],
        delimiter: str,
        metadata: dict[str, Any],
        column_specs: dict[str, dict[str, Any]],
        encoding: str = "utf-8",
    ) -> SimilarAnalysisSession:
        with self._lock:
            self._cleanup_expired_locked()
            session = SimilarAnalysisSession(
                analysis_id=self._next_analysis_id_locked(),
                file_name=file_name,
                rows=rows,
                header=header,
                delimiter=delimiter,
                metadata=metadata,
                column_specs=column_specs,
                encoding=encoding,
            )
            self._write_session(session)
        return session

    def get(self, analysis_id: str) -> SimilarAnalysisSession:
        with self._lock:
            path = self._session_path(analysis_id)
            if not path.exists():
                raise AnalysisNotFoundError(
                    f"analysis_id '{analysis_id}' не найден.",
                    details={"analysis_id": analysis_id},
                )
            session = self._read_session(analysis_id)
            if self._is_expired(session):
                path.unlink(missing_ok=True)
                raise AnalysisNotFoundError(
                    f"analysis_id '{analysis_id}' истек.",
                    details={"analysis_id": analysis_id},
                )
        return session


_upload_store = UploadStore()
_similar_analysis_store = SimilarAnalysisStore()


def get_upload_store() -> UploadStore:
    return _upload_store


def get_similar_analysis_store() -> SimilarAnalysisStore:
    return _similar_analysis_store
