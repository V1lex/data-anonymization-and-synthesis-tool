from sda.use_cases.analyze_columns import analyze_columns


def test_analyze_columns_suggests_generalize_year_for_birth_date() -> None:
    rows = [
        {"birth_date": "1991-04-08"},
        {"birth_date": "1987-11-02"},
    ]

    columns = analyze_columns(header=["birth_date"], rows=rows)

    assert columns[0]["detected_type"] == "birth_date"
    assert columns[0]["suggested_method"] == "generalize_year"


def test_analyze_columns_suggests_mask_for_email() -> None:
    rows = [
        {"email": "alice@example.com"},
        {"email": "bob@example.com"},
    ]

    columns = analyze_columns(header=["email"], rows=rows)

    assert columns[0]["detected_type"] == "email"
    assert columns[0]["suggested_method"] == "mask"


def test_analyze_columns_suggests_keep_for_status() -> None:
    rows = [
        {"status": "new"},
        {"status": "paid"},
        {"status": "cancelled"},
    ]

    columns = analyze_columns(header=["status"], rows=rows)

    assert columns[0]["detected_type"] == "category"
    assert columns[0]["suggested_method"] == "keep"


def test_analyze_columns_suggests_pseudonymize_for_vehicle_plate() -> None:
    rows = [
        {"vehicle_plate": "A123BC77"},
        {"vehicle_plate": "X777XX99"},
    ]

    columns = analyze_columns(header=["vehicle_plate"], rows=rows)

    assert columns[0]["detected_type"] == "vehicle_plate"
    assert columns[0]["suggested_method"] == "pseudonymize"
    assert columns[0]["reason"]
    assert columns[0]["hint"]


def test_analyze_columns_suggests_redact_for_free_text_comments() -> None:
    rows = [
        {"comment": "User wrote that their phone is +7 999 111-22-33 and asked for callback."},
        {"comment": "Customer mentioned passport details in free text and wants deletion."},
    ]

    columns = analyze_columns(header=["comment"], rows=rows)

    assert columns[0]["detected_type"] == "text"
    assert columns[0]["suggested_method"] == "redact"
