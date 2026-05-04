import base64
import csv
import io
import zipfile

from sda.use_cases.similar_csv import (
    prepare_similar_analysis,
    prepare_similar_multi_analysis,
    run_similar_group_use_case,
    run_similar_use_case,
)


class FakeMultiSimilarService:
    def analyze(self, *, rows, header, preview_rows_limit):
        columns = []
        column_specs = {}
        for column_name in header:
            values = [row.get(column_name, "") for row in rows]
            non_empty = [value for value in values if value]
            is_id = column_name == "id" or column_name.endswith("_id")
            is_unique = len(set(non_empty)) == len(non_empty)
            column_specs[column_name] = {
                "name": column_name,
                "display_type": "id" if is_id else "category",
                "sdtype": "id" if is_id else "categorical",
                "datetime_format": None,
                "boolean_true_value": None,
                "boolean_false_value": None,
                "numerical_kind": None,
                "id_strategy": "auto_increment" if is_id and is_unique else None,
                "sequence_start": 1 if is_id and is_unique else None,
                "sequence_step": 1 if is_id and is_unique else None,
                "sequence_width": None,
                "sequence_prefix": None,
                "sequence_suffix": None,
            }
            columns.append(
                {
                    "name": column_name,
                    "inferred_type": column_specs[column_name]["display_type"],
                    "null_ratio": 0.0,
                    "unique_ratio": len(set(non_empty)) / max(len(non_empty), 1),
                    "sample_values": non_empty[:5],
                }
            )
        return {
            "metadata": {},
            "column_specs": column_specs,
            "columns": columns,
            "preview_rows": rows[:preview_rows_limit],
            "summary": [f"rows: {len(rows)}"],
            "warnings": [],
        }

    def synthesize_multi(self, *, tables, relationships, target_rows_by_table):
        return {
            "tables": {
                table_name: [
                    {
                        column_name: (
                            str((index % 2) + 1)
                            if table_name == "orders" and column_name == "user_id"
                            else str(index + 1) if column_name.endswith("_id") else f"{column_name}-{index + 1}"
                        )
                        for column_name in table_payload["header"]
                    }
                    for index in range(target_rows_by_table[table_name])
                ]
                for table_name, table_payload in tables.items()
            },
            "warnings": [],
        }


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


def test_similar_multi_analysis_infers_relationships_between_uploaded_tables() -> None:
    analysis = prepare_similar_multi_analysis(
        files=[
            {
                "file_name": "users.csv",
                "content": (
                    "user_id,name\n"
                    "1,Alice\n"
                    "2,Bob\n"
                ).encode("utf-8"),
            },
            {
                "file_name": "orders.csv",
                "content": (
                    "order_id,user_id,total\n"
                    "10,1,100\n"
                    "11,2,200\n"
                    "12,1,150\n"
                ).encode("utf-8"),
            },
        ],
        service=FakeMultiSimilarService(),
    )

    assert [table["table_name"] for table in analysis["tables"]] == ["users", "orders"]
    assert analysis["relationships"] == [
        {
            "parent_table_name": "users",
            "parent_primary_key": "user_id",
            "child_table_name": "orders",
            "child_foreign_key": "user_id",
        }
    ]


def test_similar_group_use_case_returns_zip_for_related_tables() -> None:
    analysis = prepare_similar_multi_analysis(
        files=[
            {"file_name": "users.csv", "content": b"user_id,name\n1,Alice\n2,Bob\n"},
            {"file_name": "orders.csv", "content": b"order_id,user_id,total\n10,1,100\n11,2,200\n"},
        ],
        service=FakeMultiSimilarService(),
    )

    result = run_similar_group_use_case(
        group_id="grp_test",
        tables=analysis["tables"],
        relationships=analysis["relationships"],
        target_rows_by_table={"users": 2, "orders": 3},
        service=FakeMultiSimilarService(),
    )

    archive_bytes = base64.b64decode(result["archive_base64"])
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes))

    assert result["result_format"] == "zip_base64"
    assert result["total_rows"] == 5
    assert sorted(archive.namelist()) == ["orders_similar.csv", "users_similar.csv"]
    orders = list(csv.DictReader(io.StringIO(archive.read("orders_similar.csv").decode("utf-8"))))
    assert len(orders) == 3
    assert set(row["user_id"] for row in orders).issubset({"1", "2"})
