import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from tempfile import gettempdir
from threading import Lock
from typing import Any

from sda.core.domain.limits import UPLOAD_TTL_SECONDS
from sda.core.domain.errors import (
    AnalysisNotFoundError,
    SimilarJobNotFoundError,
    TemplateNotFoundError,
    UploadNotFoundError,
)

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
SIMILAR_GROUP_STORE_DIR = Path(gettempdir()) / "sda_similar_group_store"
SIMILAR_GROUP_ID_PREFIX = "grp_"
SIMILAR_JOB_STORE_DIR = Path(gettempdir()) / "sda_similar_job_store"
SIMILAR_JOB_ID_PREFIX = "job_"


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
    table_name: str
    rows: list[dict[str, str]]
    header: list[str]
    delimiter: str
    metadata: dict[str, Any]
    column_specs: dict[str, dict[str, Any]]
    encoding: str = "utf-8"
    created_at: float = field(default_factory=time.time)


@dataclass
class SimilarAnalysisGroupSession:
    group_id: str
    analysis_ids: list[str]
    relationships: list[dict[str, str]]
    created_at: float = field(default_factory=time.time)


@dataclass
class SimilarJobSession:
    job_id: str
    status: str
    kind: str
    analysis_id: str | None = None
    group_id: str | None = None
    target_rows: int | None = None
    target_rows_by_table: dict[str, int] = field(default_factory=dict)
    progress: float = 0.0
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    updated_at: float = field(default_factory=time.time)


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
        file_name = str(payload["file_name"])
        return SimilarAnalysisSession(
            analysis_id=str(payload["analysis_id"]),
            file_name=file_name,
            table_name=str(payload.get("table_name") or Path(file_name).stem),
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
        table_name: str | None = None,
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
                table_name=table_name or Path(file_name).stem,
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


class SimilarAnalysisGroupStore:
    def __init__(self, *, storage_dir: Path | None = None, ttl_seconds: int = UPLOAD_TTL_SECONDS) -> None:
        self._storage_dir = Path(storage_dir or SIMILAR_GROUP_STORE_DIR)
        self._ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, group_id: str) -> Path:
        return self._storage_dir / f"{group_id}.json"

    def _write_session(self, session: SimilarAnalysisGroupSession) -> None:
        path = self._session_path(session.group_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(asdict(session), ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)

    def _read_session(self, group_id: str) -> SimilarAnalysisGroupSession:
        path = self._session_path(group_id)
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return SimilarAnalysisGroupSession(
            group_id=str(payload["group_id"]),
            analysis_ids=list(payload["analysis_ids"]),
            relationships=list(payload.get("relationships", [])),
            created_at=float(payload.get("created_at", 0.0)),
        )

    def _is_expired(self, session: SimilarAnalysisGroupSession) -> bool:
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

    def _next_group_id_locked(self) -> str:
        next_value = 1
        for path in self._storage_dir.glob(f"{SIMILAR_GROUP_ID_PREFIX}*.json"):
            suffix = path.stem.removeprefix(SIMILAR_GROUP_ID_PREFIX)
            if suffix.isdigit():
                next_value = max(next_value, int(suffix) + 1)
        return f"{SIMILAR_GROUP_ID_PREFIX}{next_value}"

    def create(
        self,
        *,
        analysis_ids: list[str],
        relationships: list[dict[str, str]],
    ) -> SimilarAnalysisGroupSession:
        with self._lock:
            self._cleanup_expired_locked()
            session = SimilarAnalysisGroupSession(
                group_id=self._next_group_id_locked(),
                analysis_ids=analysis_ids,
                relationships=relationships,
            )
            self._write_session(session)
        return session

    def get(self, group_id: str) -> SimilarAnalysisGroupSession:
        with self._lock:
            path = self._session_path(group_id)
            if not path.exists():
                raise AnalysisNotFoundError(
                    f"group_id '{group_id}' не найден.",
                    details={"group_id": group_id},
                )
            session = self._read_session(group_id)
            if self._is_expired(session):
                path.unlink(missing_ok=True)
                raise AnalysisNotFoundError(
                    f"group_id '{group_id}' истек.",
                    details={"group_id": group_id},
                )
        return session


class SimilarJobStore:
    def __init__(self, *, storage_dir: Path | None = None, ttl_seconds: int = UPLOAD_TTL_SECONDS) -> None:
        self._storage_dir = Path(storage_dir or SIMILAR_JOB_STORE_DIR)
        self._ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, job_id: str) -> Path:
        return self._storage_dir / f"{job_id}.json"

    def _write_session(self, session: SimilarJobSession) -> None:
        path = self._session_path(session.job_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(asdict(session), ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)

    def _read_session(self, job_id: str) -> SimilarJobSession:
        path = self._session_path(job_id)
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return SimilarJobSession(
            job_id=str(payload["job_id"]),
            status=str(payload["status"]),
            kind=str(payload["kind"]),
            analysis_id=payload.get("analysis_id"),
            group_id=payload.get("group_id"),
            target_rows=payload.get("target_rows"),
            target_rows_by_table=dict(payload.get("target_rows_by_table", {})),
            progress=float(payload.get("progress", 0.0)),
            result=payload.get("result"),
            error=payload.get("error"),
            created_at=float(payload.get("created_at", 0.0)),
            started_at=payload.get("started_at"),
            finished_at=payload.get("finished_at"),
            updated_at=float(payload.get("updated_at", 0.0)),
        )

    def _is_expired(self, session: SimilarJobSession) -> bool:
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

    def _next_job_id_locked(self) -> str:
        next_value = 1
        for path in self._storage_dir.glob(f"{SIMILAR_JOB_ID_PREFIX}*.json"):
            suffix = path.stem.removeprefix(SIMILAR_JOB_ID_PREFIX)
            if suffix.isdigit():
                next_value = max(next_value, int(suffix) + 1)
        return f"{SIMILAR_JOB_ID_PREFIX}{next_value}"

    def create_single(self, *, analysis_id: str, target_rows: int) -> SimilarJobSession:
        with self._lock:
            self._cleanup_expired_locked()
            session = SimilarJobSession(
                job_id=self._next_job_id_locked(),
                status="queued",
                kind="single_table",
                analysis_id=analysis_id,
                target_rows=target_rows,
            )
            self._write_session(session)
        return session

    def create_group(self, *, group_id: str, target_rows_by_table: dict[str, int]) -> SimilarJobSession:
        with self._lock:
            self._cleanup_expired_locked()
            session = SimilarJobSession(
                job_id=self._next_job_id_locked(),
                status="queued",
                kind="multi_table",
                group_id=group_id,
                target_rows_by_table=target_rows_by_table,
            )
            self._write_session(session)
        return session

    def get(self, job_id: str) -> SimilarJobSession:
        with self._lock:
            path = self._session_path(job_id)
            if not path.exists():
                raise SimilarJobNotFoundError(
                    f"job_id '{job_id}' не найден.",
                    details={"job_id": job_id},
                )
            session = self._read_session(job_id)
            if self._is_expired(session):
                path.unlink(missing_ok=True)
                raise SimilarJobNotFoundError(
                    f"job_id '{job_id}' истек.",
                    details={"job_id": job_id},
                )
        return session

    def update(self, job_id: str, **changes: Any) -> SimilarJobSession:
        with self._lock:
            path = self._session_path(job_id)
            if not path.exists():
                raise SimilarJobNotFoundError(
                    f"job_id '{job_id}' не найден.",
                    details={"job_id": job_id},
                )
            session = self._read_session(job_id)
            if self._is_expired(session):
                path.unlink(missing_ok=True)
                raise SimilarJobNotFoundError(
                    f"job_id '{job_id}' истек.",
                    details={"job_id": job_id},
                )
            for key, value in changes.items():
                setattr(session, key, value)
            session.updated_at = time.time()
            self._write_session(session)
        return session


_upload_store = UploadStore()
_similar_analysis_store = SimilarAnalysisStore()
_similar_group_store = SimilarAnalysisGroupStore()
_similar_job_store = SimilarJobStore()


def get_upload_store() -> UploadStore:
    return _upload_store


def get_similar_analysis_store() -> SimilarAnalysisStore:
    return _similar_analysis_store


def get_similar_group_store() -> SimilarAnalysisGroupStore:
    return _similar_group_store


def get_similar_job_store() -> SimilarJobStore:
    return _similar_job_store
