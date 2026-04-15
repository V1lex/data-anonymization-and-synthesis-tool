from typing import Any, Sequence

from sda.core.anonymization.field_detector import FieldDetector
from sda.core.anonymization.method_suggester import MethodSuggester


def _build_detection_sample(values: Sequence[str], *, max_values: int = 25) -> list[str]:
    non_empty_values = [value for value in values if value and value.strip()]
    if len(non_empty_values) <= max_values:
        return non_empty_values

    step = (len(non_empty_values) - 1) / (max_values - 1)
    indexes = {round(step * index) for index in range(max_values)}
    return [non_empty_values[index] for index in sorted(indexes)]


def analyze_columns(
    *,
    header: Sequence[str],
    rows: Sequence[dict[str, str]],
) -> list[dict[str, Any]]:
    detector = FieldDetector()
    suggester = MethodSuggester()
    column_descriptions: list[dict[str, Any]] = []
    total_rows = len(rows) or 1

    for index, column_name in enumerate(header):
        values = [row.get(column_name, "") for row in rows]
        non_empty_values = [value for value in values if value and value.strip()]
        sample_values = non_empty_values[:5]
        detection_values = _build_detection_sample(non_empty_values or values)
        unique_ratio = len(set(non_empty_values)) / max(len(non_empty_values), 1)
        null_ratio = 1.0 - (len(non_empty_values) / total_rows)

        detection = detector.detect(column_name=column_name, values=detection_values or list(values))
        suggestion = suggester.suggest(
            column_name=column_name,
            detection=detection,
            sample_values=sample_values,
            unique_ratio=unique_ratio,
            null_ratio=null_ratio,
        )

        column_descriptions.append(
            {
                "index": index,
                "name": column_name,
                "inferred_type": detection.detected_type,
                "detected_type": detection.detected_type,
                "sample_values": sample_values[:2],
                "null_ratio": round(null_ratio, 4),
                "unique_ratio": round(unique_ratio, 4),
                "reason": detection.reason,
                "suggested_method": suggestion.suggested_method,
                "confidence": round(suggestion.confidence, 2),
                "hint": suggestion.hint,
            }
        )

    return column_descriptions
