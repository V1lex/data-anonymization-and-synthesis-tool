import base64
import csv
import io
import time

from fastapi.testclient import TestClient

from sda.web.app import app
from sda.web.deps import (
    SimilarAnalysisGroupStore,
    SimilarAnalysisStore,
    SimilarJobStore,
    get_similar_analysis_store,
    get_similar_group_store,
    get_similar_job_store,
)

client = TestClient(app)


def _build_orders_csv() -> bytes:
    return (
        "order_id,amount,status,created_at\n"
        "1,10.5,new,2024-01-01\n"
        "2,20.0,paid,2024-01-02\n"
        "3,15.2,paid,2024-01-03\n"
        "4,18.1,cancelled,2024-01-04\n"
        "5,30.0,new,2024-01-05\n"
        "6,22.4,paid,2024-01-06\n"
    ).encode("utf-8")


def test_post_similar_analyze_returns_profiles_and_preview() -> None:
    response = client.post(
        "/api/v1/similar/analyze",
        files={"file": ("orders.csv", _build_orders_csv(), "text/csv")},
        data={"has_header": "true", "preview_rows_limit": "3"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"].startswith("ana_")
    assert payload["file_name"] == "orders.csv"
    assert payload["row_count"] == 6
    assert payload["column_count"] == 4
    assert len(payload["preview_rows"]) == 3

    columns = {item["name"]: item for item in payload["columns"]}
    assert columns["amount"]["inferred_type"] == "numerical"
    assert columns["created_at"]["inferred_type"] == "datetime"


def test_post_similar_run_returns_generated_csv() -> None:
    analyze_response = client.post(
        "/api/v1/similar/analyze",
        files={"file": ("orders.csv", _build_orders_csv(), "text/csv")},
        data={"has_header": "true"},
    )
    analyze_payload = analyze_response.json()

    run_response = client.post(
        "/api/v1/similar/run",
        json={
            "analysis_id": analyze_payload["analysis_id"],
            "target_rows": 4,
        },
    )

    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["analysis_id"] == analyze_payload["analysis_id"]
    assert payload["file_name"] == "orders_similar.csv"
    assert payload["row_count"] == 4
    assert payload["column_count"] == 4
    assert payload["result_format"] == "csv_base64"

    decoded = base64.b64decode(payload["content_base64"]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(decoded)))
    assert len(rows) == 4
    assert set(rows[0]) == {"order_id", "amount", "status", "created_at"}
    assert [row["order_id"] for row in rows] == ["1", "2", "3", "4"]
    assert rows[0]["created_at"]


def test_post_similar_analyze_rejects_non_csv() -> None:
    response = client.post(
        "/api/v1/similar/analyze",
        files={"file": ("notes.txt", b"hello", "text/plain;charset=utf-8")},
        data={"has_header": "true"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "invalid_file_type"


def test_post_similar_run_returns_analysis_not_found() -> None:
    response = client.post(
        "/api/v1/similar/run",
        json={
            "analysis_id": "ana_999999",
            "target_rows": 3,
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error_code"] == "analysis_not_found"


def test_post_similar_job_tracks_async_status(monkeypatch, tmp_path) -> None:
    from sda.web.routers import similar as similar_router

    analysis_store = SimilarAnalysisStore(storage_dir=tmp_path / "analysis", ttl_seconds=60)
    group_store = SimilarAnalysisGroupStore(storage_dir=tmp_path / "groups", ttl_seconds=60)
    job_store = SimilarJobStore(storage_dir=tmp_path / "jobs", ttl_seconds=60)
    session = analysis_store.create(
        file_name="orders.csv",
        rows=[{"order_id": "1"}, {"order_id": "2"}],
        header=["order_id"],
        delimiter=",",
        metadata={},
        column_specs={},
    )

    def fake_run_similar_use_case(**_):
        return {
            "analysis_id": session.analysis_id,
            "file_name": "orders_similar.csv",
            "row_count": 2,
            "column_count": 1,
            "result_format": "csv_base64",
            "content_base64": base64.b64encode(b"order_id\n1\n2\n").decode("ascii"),
            "warnings": [],
        }

    monkeypatch.setattr(similar_router, "run_similar_use_case", fake_run_similar_use_case)
    app.dependency_overrides[get_similar_analysis_store] = lambda: analysis_store
    app.dependency_overrides[get_similar_group_store] = lambda: group_store
    app.dependency_overrides[get_similar_job_store] = lambda: job_store

    try:
        response = client.post(
            "/api/v1/similar/jobs",
            json={"analysis_id": session.analysis_id, "target_rows": 2},
        )

        assert response.status_code == 202
        job_payload = response.json()
        assert job_payload["job_id"].startswith("job_")
        assert job_payload["status"] == "queued"

        status_payload = {}
        for _ in range(50):
            status_response = client.get(job_payload["status_url"])
            assert status_response.status_code == 200
            status_payload = status_response.json()
            if status_payload["status"] == "succeeded":
                break
            time.sleep(0.02)

        assert status_payload["status"] == "succeeded"
        assert status_payload["progress"] == 1.0
        assert status_payload["result"]["file_name"] == "orders_similar.csv"
    finally:
        app.dependency_overrides.clear()
