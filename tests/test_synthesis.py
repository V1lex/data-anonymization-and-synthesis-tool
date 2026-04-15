import base64
import csv
import io

from sda.use_cases.similar_csv import prepare_similar_analysis, run_similar_use_case


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
