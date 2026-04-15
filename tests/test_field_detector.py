from sda.core.anonymization.field_detector import FieldDetector


detector = FieldDetector()


def test_field_detector_recognizes_email() -> None:
    result = detector.detect(
        column_name="email",
        values=["alice@example.com", "bob@example.com"],
    )

    assert result.detected_type == "email"
    assert result.confidence >= 0.9


def test_field_detector_recognizes_mixed_date_formats() -> None:
    result = detector.detect(
        column_name="created_at",
        values=["2024-01-01", "02.01.2024", "2024-01-03T10:15:00"],
    )

    assert result.detected_type in {"date", "datetime"}


def test_field_detector_recognizes_unix_timestamps() -> None:
    result = detector.detect(
        column_name="event_timestamp",
        values=["1714564800", "1714651200", "1714737600"],
    )

    assert result.detected_type == "datetime"


def test_field_detector_recognizes_vehicle_plate() -> None:
    result = detector.detect(
        column_name="vehicle_plate",
        values=["A123BC77", "X777XX99"],
    )

    assert result.detected_type == "vehicle_plate"


def test_field_detector_recognizes_identifier() -> None:
    result = detector.detect(
        column_name="customer_id",
        values=["usr_1001", "usr_1002", "usr_1003"],
    )

    assert result.detected_type == "id_like"


def test_field_detector_recognizes_single_name_columns() -> None:
    result = detector.detect(
        column_name="first_name",
        values=["Alice", "Bob", "Charlie"],
    )

    assert result.detected_type == "full_name"


def test_field_detector_recognizes_camel_case_birth_date() -> None:
    result = detector.detect(
        column_name="birthDate",
        values=["1991-04-08", "1987-11-02"],
    )

    assert result.detected_type == "birth_date"


def test_field_detector_recognizes_address_and_category() -> None:
    address_result = detector.detect(
        column_name="address",
        values=["г. Москва, ул. Лесная, д. 12", "г. Казань, пр-т Победы, д. 44"],
    )
    category_result = detector.detect(
        column_name="status",
        values=["new", "paid", "cancelled", "paid"],
    )

    assert address_result.detected_type == "address"
    assert category_result.detected_type == "category"
