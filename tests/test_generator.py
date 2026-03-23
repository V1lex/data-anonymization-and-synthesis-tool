import pytest

from sda.core.domain.errors import GenerationError
from sda.core.generation.generator import DataGenerator


def test_data_generator_uses_requested_locale() -> None:
    generator = DataGenerator(locale="en_US")

    assert generator.locale == "en_US"
    assert generator.faker.locales == ["en_US"]


def test_data_generator_rejects_unsupported_locale() -> None:
    with pytest.raises(GenerationError):
        DataGenerator(locale="de_DE")
