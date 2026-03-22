from enum import Enum
from dataclasses import dataclass

from sda.core.domain.errors import InvalidRuleError


class AnonymizationMethod(str, Enum):
    """Поддерживаемые методы анонимизации в MVP."""

    KEEP = "keep"
    PSEUDONYMIZE = "pseudonymize"
    MASK = "mask"
    REDACT = "redact"
    GENERALIZE_YEAR = "generalize_year"


@dataclass(frozen=True)
class MethodSpec:
    """Формальное описание метода анонимизации."""

    code: AnonymizationMethod
    title: str
    description: str
    is_reversible: bool
    supports_text: bool
    supports_dates: bool


METHOD_SPECS: dict[AnonymizationMethod, MethodSpec] = {
    AnonymizationMethod.KEEP: MethodSpec(
        code=AnonymizationMethod.KEEP,
        title="Оставить без изменений",
        description="Возвращает исходное значение без изменений.",
        is_reversible=True,
        supports_text=True,
        supports_dates=True,
    ),
    AnonymizationMethod.PSEUDONYMIZE: MethodSpec(
        code=AnonymizationMethod.PSEUDONYMIZE,
        title="Псевдонимизация",
        description=(
            "Заменяет значение на стабильное псевдо-значение. "
            "Одинаковые входные значения должны давать одинаковый результат."
        ),
        is_reversible=False,
        supports_text=True,
        supports_dates=False,
    ),
    AnonymizationMethod.MASK: MethodSpec(
        code=AnonymizationMethod.MASK,
        title="Маскирование",
        description=(
            "Частично скрывает строковое значение, сохраняя только часть символов."
        ),
        is_reversible=False,
        supports_text=True,
        supports_dates=False,
    ),
    AnonymizationMethod.REDACT: MethodSpec(
        code=AnonymizationMethod.REDACT,
        title="Полное скрытие",
        description=(
            "Полностью заменяет значение на фиксированный маркер, например [REDACTED]."
        ),
        is_reversible=False,
        supports_text=True,
        supports_dates=True,
    ),
    AnonymizationMethod.GENERALIZE_YEAR: MethodSpec(
        code=AnonymizationMethod.GENERALIZE_YEAR,
        title="Обобщение даты до года",
        description=(
            "Извлекает из даты только год и убирает точность до месяца и дня."
        ),
        is_reversible=False,
        supports_text=False,
        supports_dates=True,
    ),
}


DEFAULT_REDACTION_VALUE = "[REDACTED]"


def get_supported_methods() -> list[str]:
    """Возвращает список кодов поддерживаемых методов."""
    return [method.value for method in AnonymizationMethod]


def get_method_spec(method: AnonymizationMethod) -> MethodSpec:
    """Возвращает описание метода анонимизации."""
    return METHOD_SPECS[method]


SUPPORTED_ANONYMIZATION_METHODS = {
    "keep",
    "mask",
    "redact",
    "pseudonymize",
    "generalize_year",
}


def ensure_supported_method(method: str) -> str:
    normalized = method.strip()
    if normalized not in SUPPORTED_ANONYMIZATION_METHODS:
        supported = ", ".join(sorted(SUPPORTED_ANONYMIZATION_METHODS))
        raise InvalidRuleError(
            f"Неподдерживаемый метод анонимизации '{method}'. Ожидались: {supported}.",
            details={
                "method": method,
                "supported_methods": sorted(SUPPORTED_ANONYMIZATION_METHODS),
            },
        )
    return normalized
