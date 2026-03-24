import pytest
from uuid import UUID

from sda.core.domain.errors import GenerationError
from sda.core.generation.generator import DataGenerator


def test_data_generator_uses_requested_locale() -> None:
    generator = DataGenerator(locale="en_US")
    assert generator.locale == "en_US"
    assert generator.faker.locales == ["en_US"]


def test_data_generator_rejects_unsupported_locale() -> None:
    with pytest.raises(GenerationError):
        DataGenerator(locale="de_DE")


def test_load_template_missing_file() -> None:
    generator = DataGenerator()
    with pytest.raises(GenerationError, match="не найден"):
        generator.load_template("non_existent_template_999")


def test_generate_table_invalid_count() -> None:
    generator = DataGenerator()
    with pytest.raises(GenerationError, match="больше нуля"):
        generator.generate_table("users", 0)


def test_auto_increment_provider() -> None:
    """Проверка провайдера auto_increment."""
    generator = DataGenerator()
    col = {"name": "id", "provider": "auto_increment"}
    
    val1 = generator._generate_column_value("test_table", col)
    val2 = generator._generate_column_value("test_table", col)
    
    assert val1 == 1
    assert val2 == 2

    col2 = {"name": "other_id", "provider": "auto_increment"}
    val3 = generator._generate_column_value("test_table", col2)
    assert val3 == 1


def test_core_faker_providers() -> None:
    """Проверка базовых провайдеров."""
    generator = DataGenerator()

    val_uuid = generator._generate_column_value("test", {"name": "u", "provider": "uuid4"})
    assert UUID(str(val_uuid))
    
    val_int = generator._generate_column_value("test", {"name": "i", "provider": "random_int", "min": 10, "max": 20})
    assert isinstance(val_int, int)
    assert 10 <= val_int <= 20
    
    val_elem = generator._generate_column_value("test", {"name": "e", "provider": "random_element", "elements": ["A", "B", "C"]})
    assert val_elem in ["A", "B", "C"]
    
    val_bool = generator._generate_column_value("test", {"name": "b", "provider": "boolean"})
    assert isinstance(val_bool, bool)
    
    val_dt = generator._generate_column_value("test", {"name": "dt", "provider": "date_time_between"})
    assert isinstance(val_dt, str)
    assert "T" in val_dt or "-" in val_dt
    
    val_dob = generator._generate_column_value("test", {"name": "dob", "provider": "date_of_birth", "minimum_age": 18, "maximum_age": 90})
    assert isinstance(val_dob, str)
    assert len(val_dob.split("-")) == 3


def test_generic_faker_fallback() -> None:
    """Проверка вызова любого метода Faker без параметров."""
    generator = DataGenerator()

    val_word = generator._generate_column_value("test", {"name": "w", "provider": "word"})
    assert isinstance(val_word, str)
    assert len(val_word) > 0
    
    val_name = generator._generate_column_value("test", {"name": "n", "provider": "name"})
    assert isinstance(val_name, str)
    assert len(val_name) > 0


def test_unsupported_provider_raises_error() -> None:
    """Проверка выброса GenerationError при неизвестном провайдере."""
    generator = DataGenerator()
    col = {"name": "bad_col", "provider": "unknown_super_faker_method"}
    
    with pytest.raises(GenerationError, match="Неподдерживаемый provider"):
        generator._generate_column_value("test_table", col)


def test_random_int_invalid_bounds_raises_error() -> None:
    """Проверка валидации лимитов для random_int."""
    generator = DataGenerator()
    col = {"name": "i", "provider": "random_int", "min": 100, "max": 10}
    
    with pytest.raises(GenerationError, match="некорректный диапазон"):
        generator._generate_column_value("test_table", col)
