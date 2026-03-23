import hashlib
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from faker import Faker

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
EMAIL_COLUMN_PATTERN = re.compile(r"email", re.IGNORECASE)
PHONE_COLUMN_PATTERN = re.compile(r"phone|mobile|tel", re.IGNORECASE)
NAME_COLUMN_PATTERN = re.compile(r"full_name|first_name|last_name|name|operator", re.IGNORECASE)
CITY_COLUMN_PATTERN = re.compile(r"city|town", re.IGNORECASE)
ADDRESS_COLUMN_PATTERN = re.compile(r"address|street|location", re.IGNORECASE)
IDENTIFIER_COLUMN_PATTERN = re.compile(r"(^id$|_id$|uuid|identifier)", re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+")
CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")
PHONE_ALLOWED_PATTERN = re.compile(r"^[\d\s()+\-._]+$")


def _mask_segment(segment: str, *, keep_start: int = 1, keep_end: int = 0) -> str:
    if not segment:
        return segment
    if len(segment) == 1:
        return "*"
    if len(segment) == 2:
        return f"{segment[:1]}*"

    visible_start = min(keep_start, len(segment) - 1)
    visible_end = min(keep_end, len(segment) - visible_start - 1)
    masked_length = max(1, len(segment) - visible_start - visible_end)
    return (
        segment[:visible_start]
        + ("*" * masked_length)
        + (segment[-visible_end:] if visible_end else "")
    )


def _looks_like_phone(value: str) -> bool:
    stripped = value.strip()
    digits = [char for char in stripped if char.isdigit()]
    return 7 <= len(digits) <= 15 and bool(PHONE_ALLOWED_PATTERN.match(stripped))


def _looks_like_name(value: str) -> bool:
    tokens = re.findall(r"[A-Za-zА-Яа-яЁё]+", value)
    return 1 <= len(tokens) <= 4 and all(len(token) >= 2 for token in tokens)


def _looks_like_identifier(column_name: str) -> bool:
    return bool(IDENTIFIER_COLUMN_PATTERN.search(column_name))


def _mask_email(value: str) -> str:
    local_part, _, domain = value.partition("@")
    if not local_part or not domain:
        return _mask_text(value)
    masked_local = local_part[:1] + "***"
    return f"{masked_local}@{domain}"


def _mask_phone(value: str) -> str:
    digits_total = sum(char.isdigit() for char in value)
    if digits_total <= 2:
        return re.sub(r"\d", "*", value)

    digits_to_keep = 2
    current_digit = 0
    masked_chars: list[str] = []
    for char in value:
        if char.isdigit():
            current_digit += 1
            if current_digit <= digits_total - digits_to_keep:
                masked_chars.append("*")
            else:
                masked_chars.append(char)
        else:
            masked_chars.append(char)
    return "".join(masked_chars)


def _mask_text(value: str) -> str:
    if not value:
        return value
    if EMAIL_PATTERN.match(value):
        return _mask_email(value)
    if _looks_like_phone(value):
        return _mask_phone(value)

    return TOKEN_PATTERN.sub(
        lambda match: _mask_segment(
            match.group(0),
            keep_start=1,
            keep_end=1 if len(match.group(0)) >= 6 else 0,
        ),
        value,
    )


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
        raise InvalidRuleError("Метод 'Обобщение до года' применим только к датам и datetime-значениям.")
    return match.group(0)


class CsvAnonymizer:
    """Применяет набор правил к произвольному табличному CSV."""

    def __init__(self) -> None:
        self._pseudonym_cache: dict[tuple[str, str], str] = {}
        self._pseudonym_counters: dict[str, int] = {}
        self._used_pseudonyms: dict[str, set[str]] = {}

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

        for column_name, rule in rules.items():
            if str(rule.get("method", "keep")) != "pseudonymize":
                continue
            unique_values = sorted(
                {
                    str(row.get(column_name, ""))
                    for row in rows
                    if str(row.get(column_name, "")).strip()
                }
            )
            for unique_value in unique_values:
                self._ensure_pseudonym(column_name=column_name, value=unique_value)

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
                return _mask_email(value)
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
        return self._ensure_pseudonym(column_name=column_name, value=value)

    def _ensure_pseudonym(self, *, column_name: str, value: str) -> str:
        cache_key = (column_name, value)
        cached = self._pseudonym_cache.get(cache_key)
        if cached is not None:
            return cached

        sequence_index = self._pseudonym_counters.get(column_name, 0) + 1
        self._pseudonym_counters[column_name] = sequence_index

        candidate = self._generate_pseudonym(
            column_name=column_name,
            value=value,
            sequence_index=sequence_index,
        )
        used_values = self._used_pseudonyms.setdefault(column_name, set())
        attempt = 1
        while candidate in used_values:
            candidate = self._generate_pseudonym(
                column_name=column_name,
                value=value,
                sequence_index=sequence_index,
                attempt=attempt,
            )
            attempt += 1

        self._pseudonym_cache[cache_key] = candidate
        used_values.add(candidate)
        return candidate

    def _generate_pseudonym(
        self,
        *,
        column_name: str,
        value: str,
        sequence_index: int,
        attempt: int = 0,
    ) -> str:
        strategy = self._detect_pseudonym_strategy(column_name=column_name, value=value)
        if strategy == "numeric_id":
            return str(sequence_index)
        if strategy == "text_id":
            return f"id_{sequence_index}"

        locale = "ru_RU" if CYRILLIC_PATTERN.search(value) else "en_US"
        faker = Faker(locale)
        faker.seed_instance(self._stable_seed(column_name, value, sequence_index, attempt))

        if strategy == "email":
            return faker.safe_email()
        if strategy == "phone":
            return re.sub(r"\s+", " ", faker.phone_number()).strip()
        if strategy == "name":
            return faker.name()
        if strategy == "city":
            return faker.city()
        if strategy == "address":
            return faker.address().replace("\n", ", ")

        word_count = max(1, min(3, len(re.findall(r"[A-Za-zА-Яа-яЁё]+", value))))
        return " ".join(word.capitalize() for word in faker.words(nb=word_count))

    def _detect_pseudonym_strategy(self, *, column_name: str, value: str) -> str:
        lowered_name = column_name.lower()
        if EMAIL_COLUMN_PATTERN.search(lowered_name) or EMAIL_PATTERN.match(value):
            return "email"
        if PHONE_COLUMN_PATTERN.search(lowered_name) or _looks_like_phone(value):
            return "phone"
        if NAME_COLUMN_PATTERN.search(lowered_name) or _looks_like_name(value):
            return "name"
        if CITY_COLUMN_PATTERN.search(lowered_name):
            return "city"
        if ADDRESS_COLUMN_PATTERN.search(lowered_name):
            return "address"
        if _looks_like_identifier(lowered_name):
            return "numeric_id" if value.strip().isdigit() else "text_id"
        return "text"

    @staticmethod
    def _stable_seed(column_name: str, value: str, sequence_index: int, attempt: int) -> int:
        payload = f"{column_name}|{value}|{sequence_index}|{attempt}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        return int.from_bytes(digest[:8], "big")
