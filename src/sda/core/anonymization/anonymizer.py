import hashlib
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from sda.core.domain.errors import InvalidRuleError, UnknownColumnError

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)
YEAR_PATTERN = re.compile(r"(19|20)\d{2}")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _mask_text(value: str) -> str:
    if not value:
        return value
    return "".join("*" if char.isalnum() else char for char in value)


def _generalize_year(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return stripped

    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(stripped, fmt)
            return str(parsed.year)
        except ValueError:
            continue

    match = YEAR_PATTERN.search(stripped)
    if match is None:
        raise InvalidRuleError("Метод generalize_year применим только к date-like значениям.")
    return match.group(0)


class CsvAnonymizer:
    """Применяет набор правил к произвольному табличному CSV."""

    def __init__(self) -> None:
        self._pseudonym_cache: dict[tuple[str, str], str] = {}

    def anonymize_rows(
        self,
        rows: Sequence[Mapping[str, Any]],
        rules: Mapping[str, Mapping[str, Any]],
    ) -> list[dict[str, str]]:
        if not rows:
            return []

        available_columns = set(rows[0].keys())
        unknown_columns = sorted(set(rules) - available_columns)
        if unknown_columns:
            raise UnknownColumnError(
                f"Правила ссылаются на неизвестные колонки: {', '.join(unknown_columns)}.",
                details={"columns": unknown_columns},
            )

        anonymized: list[dict[str, str]] = []
        for row in rows:
            transformed_row: dict[str, str] = {}
            for column_name, value in row.items():
                rule = rules.get(column_name, {"method": "keep", "params": {}})
                transformed_row[column_name] = self._apply_rule(
                    column_name=column_name,
                    value="" if value is None else str(value),
                    method=str(rule.get("method", "keep")),
                    params=dict(rule.get("params") or {}),
                )
            anonymized.append(transformed_row)
        return anonymized

    def _apply_rule(
        self,
        *,
        column_name: str,
        value: str,
        method: str,
        params: dict[str, Any],
    ) -> str:
        if method == "keep":
            return value
        if method == "mask":
            if params.get("keep_domain") and EMAIL_PATTERN.match(value):
                local_part, _, domain = value.partition("@")
                masked_local = local_part[:1] + "***" if local_part else "***"
                return f"{masked_local}@{domain}"
            return _mask_text(value)
        if method == "redact":
            return "[REDACTED]" if value else ""
        if method == "pseudonymize":
            return self._pseudonymize(column_name=column_name, value=value)
        if method == "generalize_year":
            return _generalize_year(value)
        raise InvalidRuleError(f"Метод '{method}' не поддерживается.")

    def _pseudonymize(self, *, column_name: str, value: str) -> str:
        if not value:
            return value
        cache_key = (column_name, value)
        if cache_key not in self._pseudonym_cache:
            digest = hashlib.sha256(f"{column_name}:{value}".encode("utf-8")).hexdigest()
            self._pseudonym_cache[cache_key] = f"pseudo_{digest[:12]}"
        return self._pseudonym_cache[cache_key]
