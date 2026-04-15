from dataclasses import dataclass

from sda.core.anonymization.field_detector import FieldDetection
from sda.core.anonymization.rules import AnonymizationMethod

SAFE_CATEGORY_TOKENS = {"status", "state", "priority", "type", "category", "currency", "country", "region", "city", "segment"}
FREE_TEXT_TOKENS = {"message", "comment", "description", "note", "text", "details", "reason", "body", "content"}


@dataclass(frozen=True)
class MethodSuggestion:
    suggested_method: str
    confidence: float
    hint: str


class MethodSuggester:
    def suggest(
        self,
        *,
        column_name: str,
        detection: FieldDetection,
        sample_values: list[str],
        unique_ratio: float = 0.0,
        null_ratio: float = 0.0,
    ) -> MethodSuggestion:
        lowered_name = column_name.lower()
        detected_type = detection.detected_type

        if detected_type == "email":
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.MASK.value,
                confidence=0.96,
                hint="Email обычно лучше маскировать, сохраняя структуру адреса.",
            )

        if detected_type == "phone":
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.MASK.value,
                confidence=0.95,
                hint="Телефон лучше маскировать, чтобы сохранить читаемость формата.",
            )

        if detected_type == "full_name":
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.PSEUDONYMIZE.value,
                confidence=0.92,
                hint="Имена обычно лучше псевдонимизировать, чтобы одинаковые значения оставались одинаковыми.",
            )

        if detected_type == "address":
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.REDACT.value,
                confidence=0.9,
                hint="Полный адрес почти всегда чувствителен, поэтому по умолчанию безопаснее скрыть его целиком.",
            )

        if detected_type in {"vehicle_plate", "id_like"}:
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.PSEUDONYMIZE.value,
                confidence=0.89,
                hint="Идентификаторы и номера обычно лучше стабильно псевдонимизировать.",
            )

        if detected_type == "birth_date":
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.GENERALIZE_YEAR.value,
                confidence=0.95,
                hint="Для даты рождения обычно достаточно оставить только год.",
            )

        if detected_type in {"date", "datetime"}:
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.GENERALIZE_YEAR.value,
                confidence=0.8,
                hint="Дата может раскрывать личную информацию, поэтому часто её обобщают до года.",
            )

        if any(token in lowered_name for token in FREE_TEXT_TOKENS) or detected_type == "text":
            average_length = sum(len(value) for value in sample_values) / max(len(sample_values), 1) if sample_values else 0.0
            if average_length >= 24 or unique_ratio >= 0.7:
                return MethodSuggestion(
                    suggested_method=AnonymizationMethod.REDACT.value,
                    confidence=0.82,
                    hint="Свободный текст часто содержит PII, поэтому безопаснее скрыть его целиком.",
                )

        if any(token in lowered_name for token in SAFE_CATEGORY_TOKENS):
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.KEEP.value,
                confidence=0.86,
                hint="Поле похоже на служебную категорию и обычно может оставаться без изменений.",
            )

        if detected_type in {"city", "category", "boolean", "number"}:
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.KEEP.value,
                confidence=0.78,
                hint="Поле не выглядит чувствительным и обычно может оставаться без изменений.",
            )

        if null_ratio >= 0.9:
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.KEEP.value,
                confidence=0.62,
                hint="Колонка почти пустая, поэтому её можно оставить без изменений и при необходимости скрыть вручную.",
            )

        if sample_values and max(len(value) for value in sample_values) > 24:
            return MethodSuggestion(
                suggested_method=AnonymizationMethod.REDACT.value,
                confidence=0.6,
                hint="Длинные текстовые значения лучше скрывать, если в них может быть PII.",
            )

        return MethodSuggestion(
            suggested_method=AnonymizationMethod.KEEP.value,
            confidence=0.55,
            hint="Надёжных признаков чувствительного поля не найдено.",
        )
