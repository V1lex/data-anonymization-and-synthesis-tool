import base64
import csv
import io
import zipfile

from sda.use_cases.similar_csv import (
    prepare_multi_table_similar_analysis,
    prepare_similar_analysis,
    run_multi_table_similar_use_case,
    run_similar_use_case,
)


def test_similar_use_case_analyzes_and_generates_csv() -> None:
    csv_bytes = (
        "order_id,amount,status,created_at\n"
        "1,10.5,new,2024-01-01\n"
        "2,20.0,paid,2024-01-02\n"
        "3,15.2,paid,2024-01-03\n"
        "4,18.1,cancelled,2024-01-04\n"
        "5,30.0,new,2024-01-05\n"
        "6,22.4,paid,2024-01-06\n"
    ).encode("utf-8")

    analysis = prepare_similar_analysis(
        file_name="orders.csv",
        content=csv_bytes,
        preview_rows_limit=2,
    )

    assert analysis["row_count"] == 6
    assert analysis["column_count"] == 4
    columns = {item["name"]: item for item in analysis["columns"]}
    assert columns["order_id"]["inferred_type"] == "id"
    assert columns["amount"]["inferred_type"] == "numerical"
    assert columns["created_at"]["inferred_type"] == "datetime"

    result = run_similar_use_case(
        analysis_id="ana_test",
        file_name=analysis["file_name"],
        rows=analysis["rows"],
        header=analysis["header"],
        delimiter=analysis["delimiter"],
        metadata=analysis["metadata"],
        column_specs=analysis["column_specs"],
        target_rows=4,
    )

    decoded = base64.b64decode(result["content_base64"]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(decoded)))

    assert result["file_name"] == "orders_similar.csv"
    assert result["row_count"] == 4
    assert len(rows) == 4
    assert [row["order_id"] for row in rows] == ["1", "2", "3", "4"]
    assert rows[0]["amount"]
    assert rows[0]["created_at"].count("-") == 2


def test_similar_use_case_preserves_prefixed_auto_increment_ids() -> None:
    csv_bytes = (
        "ticket_id,status,created_at\n"
        "ORD-0001,new,2024-01-01\n"
        "ORD-0002,paid,2024-01-02\n"
        "ORD-0003,paid,2024-01-03\n"
        "ORD-0004,cancelled,2024-01-04\n"
    ).encode("utf-8")

    analysis = prepare_similar_analysis(
        file_name="tickets.csv",
        content=csv_bytes,
        preview_rows_limit=2,
    )

    result = run_similar_use_case(
        analysis_id="ana_prefixed",
        file_name=analysis["file_name"],
        rows=analysis["rows"],
        header=analysis["header"],
        delimiter=analysis["delimiter"],
        metadata=analysis["metadata"],
        column_specs=analysis["column_specs"],
        target_rows=3,
    )

    decoded = base64.b64decode(result["content_base64"]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(decoded)))

    assert [row["ticket_id"] for row in rows] == ["ORD-0001", "ORD-0002", "ORD-0003"]


def test_similar_use_case_works_without_id_columns() -> None:
    csv_bytes = (
        "name,city,status\n"
        "Alice,Moscow,new\n"
        "Bob,Samara,paid\n"
        "Carol,Kazan,new\n"
        "Dan,Perm,cancelled\n"
        "Eve,Ufa,paid\n"
    ).encode("utf-8")

    analysis = prepare_similar_analysis(
        file_name="people.csv",
        content=csv_bytes,
        preview_rows_limit=2,
    )

    result = run_similar_use_case(
        analysis_id="ana_no_id",
        file_name=analysis["file_name"],
        rows=analysis["rows"],
        header=analysis["header"],
        delimiter=analysis["delimiter"],
        metadata=analysis["metadata"],
        column_specs=analysis["column_specs"],
        target_rows=4,
    )

    decoded = base64.b64decode(result["content_base64"]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(decoded)))

    assert result["file_name"] == "people_similar.csv"
    assert len(rows) == 4
    assert set(rows[0]) == {"name", "city", "status"}


def test_multi_table_similar_use_case_generates_zip_with_related_tables() -> None:
    users_csv = (
        "user_id,name\n"
        "1,Alice\n"
        "2,Bob\n"
        "3,Carol\n"
        "4,Dan\n"
        "5,Eve\n"
        "6,Fay\n"
    ).encode("utf-8")
    orders_csv = (
        "order_id,user_id,amount\n"
        "1,1,10\n"
        "2,2,20\n"
        "3,1,15\n"
        "4,3,30\n"
        "5,4,25\n"
        "6,5,40\n"
    ).encode("utf-8")

    analysis = prepare_multi_table_similar_analysis(
        files=[
            {"file_name": "users.csv", "content": users_csv},
            {"file_name": "orders.csv", "content": orders_csv},
        ],
        preview_rows_limit=2,
    )

    assert analysis["tables"][0]["table_name"] == "users"
    assert analysis["tables"][1]["table_name"] == "orders"
    assert analysis["relationships"] == [
        {
            "parent_table_name": "users",
            "child_table_name": "orders",
            "parent_primary_key": "user_id",
            "child_foreign_key": "user_id",
        }
    ]

    result = run_multi_table_similar_use_case(
        analysis_id="mta_test",
        tables=analysis["stored_tables"],
        metadata=analysis["metadata"],
        table_specs=analysis["table_specs"],
        scale=1.0,
    )

    archive = zipfile.ZipFile(io.BytesIO(base64.b64decode(result["archive_base64"])))
    assert archive.namelist() == ["users_similar.csv", "orders_similar.csv"]

    users = list(csv.DictReader(io.StringIO(archive.read("users_similar.csv").decode("utf-8"))))
    orders = list(csv.DictReader(io.StringIO(archive.read("orders_similar.csv").decode("utf-8"))))
    user_ids = {row["user_id"] for row in users}

    assert result["result_format"] == "zip_base64"
    assert len(users) >= 1
    assert len(orders) >= 1
    assert {row["user_id"] for row in orders}.issubset(user_ids)


def test_multi_table_similar_use_case_supports_unrelated_tables() -> None:
    analysis = prepare_multi_table_similar_analysis(
        files=[
            {
                "file_name": "people.csv",
                "content": b"name,status\nA,new\nB,paid\nC,new\nD,paid\nE,new\n",
            },
            {
                "file_name": "cities.csv",
                "content": b"city,score\nMoscow,10\nPerm,20\nKazan,30\nUfa,40\nOmsk,50\n",
            },
        ],
    )

    result = run_multi_table_similar_use_case(
        analysis_id="mta_unrelated",
        tables=analysis["stored_tables"],
        metadata=analysis["metadata"],
        table_specs=analysis["table_specs"],
        scale=1.0,
    )

    archive = zipfile.ZipFile(io.BytesIO(base64.b64decode(result["archive_base64"])))
    assert archive.namelist() == ["people_similar.csv", "cities_similar.csv"]
