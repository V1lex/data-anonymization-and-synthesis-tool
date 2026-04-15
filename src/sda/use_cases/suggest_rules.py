from typing import Any, Sequence

from sda.use_cases.analyze_columns import analyze_columns


def suggest_rules(
    *,
    header: Sequence[str],
    rows: Sequence[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "column_name": column["name"],
            "detected_type": column["detected_type"],
            "suggested_method": column["suggested_method"],
            "confidence": column["confidence"],
            "hint": column["hint"],
        }
        for column in analyze_columns(header=header, rows=rows)
    ]
