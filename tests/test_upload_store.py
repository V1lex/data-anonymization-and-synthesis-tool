import json

import pytest

from sda.core.domain.errors import UploadNotFoundError
from sda.web.deps import UploadStore


def test_upload_store_persists_sessions_on_disk(tmp_path) -> None:
    store = UploadStore(storage_dir=tmp_path, ttl_seconds=60)

    session = store.create(
        file_name="people.csv",
        rows=[{"email": "alice@example.com"}],
        header=["email"],
        delimiter=",",
    )

    restored = UploadStore(storage_dir=tmp_path, ttl_seconds=60).get(session.upload_id)

    assert session.upload_id == "upload_1"
    assert restored.upload_id == session.upload_id
    assert restored.file_name == "people.csv"
    assert restored.rows == [{"email": "alice@example.com"}]
    assert restored.header == ["email"]


def test_upload_store_removes_expired_sessions(tmp_path) -> None:
    upload_id = "upload_999"
    payload = {
        "upload_id": upload_id,
        "file_name": "people.csv",
        "rows": [{"email": "alice@example.com"}],
        "header": ["email"],
        "delimiter": ",",
        "encoding": "utf-8",
        "created_at": 0.0,
    }
    path = tmp_path / f"{upload_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    store = UploadStore(storage_dir=tmp_path, ttl_seconds=1)

    with pytest.raises(UploadNotFoundError):
        store.get(upload_id)

    assert not path.exists()


def test_upload_store_uses_next_increment_for_new_sessions(tmp_path) -> None:
    store = UploadStore(storage_dir=tmp_path, ttl_seconds=60)

    first = store.create(
        file_name="first.csv",
        rows=[{"email": "alice@example.com"}],
        header=["email"],
        delimiter=",",
    )
    second = store.create(
        file_name="second.csv",
        rows=[{"email": "bob@example.com"}],
        header=["email"],
        delimiter=",",
    )

    assert first.upload_id == "upload_1"
    assert second.upload_id == "upload_2"
