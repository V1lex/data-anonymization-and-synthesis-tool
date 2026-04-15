import re
from dataclasses import dataclass
from datetime import UTC, datetime

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%d.%m.%Y",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d.%m.%y",
    "%d/%m/%y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%fZ",
)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^[\d\s()+\-._]{7,}$")
VEHICLE_PLATE_PATTERNS = (
    re.compile(r"^[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}$", re.IGNORECASE),
    re.compile(r"^[A-Z]{1,3}-?\d{3,4}$", re.IGNORECASE),
)
FULL_NAME_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё]+")
ADDRESS_MARKERS = ("street", "st.", "st ", "ул", "дом", "address", "road", "avenue", "просп", "ул.")
CITY_NAMES = {
    "moscow",
    "saint petersburg",
    "st petersburg",
    "saint-petersburg",
    "санкт-петербург",
    "москва",
    "новосибирск",
    "екатеринбург",
    "казань",
    "нижний новгород",
    "челябинск",
    "ростов-на-дону",
    "красноярск",
    "пермь",
    "краснодар",
    "samara",
    "самара",
    "kazan",
    "ufa",
    "perm",
    "yekaterinburg",
    "novosibirsk",
    "nizhny novgorod",
    "chelyabinsk",
}
BOOLEAN_TRUE = {"true", "1", "yes", "y", "да"}
BOOLEAN_FALSE = {"false", "0", "no", "n", "нет"}
NUMBER_PATTERN = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
TIMESTAMP_PATTERN = re.compile(r"^\d{10}(?:\d{3})?$")
EMAIL_NAME_TOKENS = {"email", "mail"}
PHONE_NAME_TOKENS = {"phone", "mobile", "tel", "telephone", "тел", "моб"}
BIRTH_DATE_NAME_TOKENS = {"birth", "birthday", "dob", "born", "рожд"}
DATETIME_NAME_TOKENS = {"created", "updated", "timestamp", "time", "datetime", "date", "registered", "ordered", "paid", "closed", "opened"}
VEHICLE_NAME_TOKENS = {"plate", "license", "license_plate", "vehicle", "car", "car_number", "номер", "госномер", "plate_number"}
FULL_NAME_TOKENS = {"full_name", "name", "first_name", "last_name", "surname", "fio", "фио", "имя", "operator", "manager", "customer_name"}
ADDRESS_NAME_TOKENS = {"address", "street", "location", "addr", "адрес", "улица", "street_address"}
CITY_NAME_TOKENS = {"city", "town", "город"}
IDENTIFIER_NAME_TOKENS = {"id", "uuid", "guid", "ref", "reference", "code", "identifier", "account", "invoice", "order_no", "sku", "article", "ticket_no", "номер"}
CATEGORY_NAME_TOKENS = {"status", "state", "priority", "type", "category", "role", "currency", "country", "region", "segment"}
TEXT_NAME_TOKENS = {"message", "comment", "description", "note", "text", "details", "reason", "body", "content"}


@dataclass(frozen=True)
class FieldDetection:
    detected_type: str
    confidence: float
    reason: str


class FieldDetector:
    def detect(self, column_name: str, values: list[str]) -> FieldDetection:
        non_empty = [str(value).strip() for value in values if value is not None and str(value).strip()]
        normalized_name = column_name.strip()
        lowered_name = normalized_name.lower()
        name_tokens = self._extract_name_tokens(normalized_name)

        if not non_empty:
            return FieldDetection(
                detected_type="text",
                confidence=0.4,
                reason="Колонка пустая или содержит только пустые значения.",
            )

        checks = [
            self._detect_email(lowered_name, name_tokens, non_empty),
            self._detect_phone(lowered_name, name_tokens, non_empty),
            self._detect_birth_date(lowered_name, name_tokens, non_empty),
            self._detect_datetime(lowered_name, name_tokens, non_empty),
            self._detect_vehicle_plate(lowered_name, name_tokens, non_empty),
            self._detect_full_name(lowered_name, name_tokens, non_empty),
            self._detect_address(lowered_name, name_tokens, non_empty),
            self._detect_city(lowered_name, name_tokens, non_empty),
            self._detect_identifier(lowered_name, name_tokens, non_empty),
            self._detect_category(lowered_name, name_tokens, non_empty),
            self._detect_free_text(lowered_name, name_tokens, non_empty),
            self._detect_boolean(lowered_name, non_empty),
            self._detect_number(lowered_name, non_empty),
        ]

        detections = [item for item in checks if item is not None]
        if detections:
            return max(detections, key=lambda item: item.confidence)

        unique_ratio = len(set(non_empty)) / max(len(non_empty), 1)
        if unique_ratio <= 0.35 or len(set(non_empty)) <= 20:
            return FieldDetection(
                detected_type="category",
                confidence=0.72,
                reason="Низкая кардинальность значений похожа на категориальное поле.",
            )

        return FieldDetection(
            detected_type="text",
            confidence=0.65,
            reason="Поле выглядит как обычный текст без устойчивого специального формата.",
        )

    def _detect_email(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        ratio = self._match_ratio(values, lambda value: bool(EMAIL_PATTERN.fullmatch(value)))
        score = 0.0
        reasons: list[str] = []
        if self._name_has_token(name_tokens, EMAIL_NAME_TOKENS):
            score += 0.5
            reasons.append("название колонки указывает на email")
        if ratio >= 0.8:
            score += 0.45
            reasons.append("значения похожи на email")
        if score < 0.75:
            return None
        return FieldDetection("email", min(0.99, score), "; ".join(reasons))

    def _detect_phone(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        ratio = self._match_ratio(values, self._looks_like_phone)
        score = 0.0
        reasons: list[str] = []
        if self._name_has_token(name_tokens, PHONE_NAME_TOKENS):
            score += 0.5
            reasons.append("название колонки указывает на телефон")
        if ratio >= 0.8:
            score += 0.4
            reasons.append("значения похожи на телефонные номера")
        if score < 0.75:
            return None
        return FieldDetection("phone", min(0.99, score), "; ".join(reasons))

    def _detect_birth_date(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        date_ratio, datetime_ratio = self._date_ratios(values)
        if not self._name_has_token(name_tokens, BIRTH_DATE_NAME_TOKENS) or max(date_ratio, datetime_ratio) < 0.75:
            return None
        return FieldDetection(
            detected_type="birth_date",
            confidence=0.96,
            reason="Название колонки и формат значений указывают на дату рождения.",
        )

    def _detect_datetime(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        date_ratio, datetime_ratio = self._date_ratios(values)
        if max(date_ratio, datetime_ratio) < 0.75:
            return None

        if datetime_ratio >= 0.6 or self._name_has_token(name_tokens, DATETIME_NAME_TOKENS) or "_at" in column_name:
            return FieldDetection(
                detected_type="datetime",
                confidence=0.9 if datetime_ratio >= 0.6 else 0.8,
                reason="Значения содержат дату и время или название колонки указывает на timestamp.",
            )

        return FieldDetection(
            detected_type="date",
            confidence=0.88,
            reason="Значения устойчиво похожи на даты.",
        )

    def _detect_vehicle_plate(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        ratio = self._match_ratio(values, self._looks_like_vehicle_plate)
        score = 0.0
        reasons: list[str] = []
        if self._name_has_token(name_tokens, VEHICLE_NAME_TOKENS):
            score += 0.5
            reasons.append("название колонки похоже на номер транспорта")
        if ratio >= 0.6:
            score += 0.35
            reasons.append("значения похожи на номера транспорта")
        if score < 0.75:
            return None
        return FieldDetection("vehicle_plate", min(0.97, score), "; ".join(reasons))

    def _detect_full_name(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        ratio = self._match_ratio(values, self._looks_like_full_name)
        single_name_ratio = self._match_ratio(values, self._looks_like_single_name)
        score = 0.0
        reasons: list[str] = []
        if self._name_has_token(name_tokens, FULL_NAME_TOKENS):
            score += 0.45
            reasons.append("название колонки указывает на имя")
        if ratio >= 0.75:
            score += 0.35
            reasons.append("значения похожи на ФИО или имена")
        elif self._name_has_token(name_tokens, FULL_NAME_TOKENS) and single_name_ratio >= 0.75:
            score += 0.3
            reasons.append("значения похожи на отдельные имена или фамилии")
        if score < 0.72:
            return None
        return FieldDetection("full_name", min(0.95, score), "; ".join(reasons))

    def _detect_address(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        ratio = self._match_ratio(values, self._looks_like_address)
        score = 0.0
        reasons: list[str] = []
        if self._name_has_token(name_tokens, ADDRESS_NAME_TOKENS):
            score += 0.5
            reasons.append("название колонки указывает на адрес")
        if ratio >= 0.5:
            score += 0.3
            reasons.append("значения похожи на адреса")
        if score < 0.72:
            return None
        return FieldDetection("address", min(0.94, score), "; ".join(reasons))

    def _detect_city(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        ratio = self._match_ratio(values, self._looks_like_city)
        score = 0.0
        reasons: list[str] = []
        if self._name_has_token(name_tokens, CITY_NAME_TOKENS):
            score += 0.5
            reasons.append("название колонки указывает на город")
        if ratio >= 0.45:
            score += 0.25
            reasons.append("значения похожи на названия городов")
        if score < 0.7:
            return None
        return FieldDetection("city", min(0.9, score), "; ".join(reasons))

    def _detect_identifier(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        unique_ratio = len(set(values)) / max(len(values), 1)
        id_like_ratio = self._match_ratio(values, self._looks_like_identifier)
        score = 0.0
        reasons: list[str] = []
        if self._name_has_token(name_tokens, IDENTIFIER_NAME_TOKENS) or column_name.endswith("_id") or column_name == "id":
            score += 0.55
            reasons.append("название колонки похоже на идентификатор")
        if unique_ratio >= 0.95:
            score += 0.2
            reasons.append("почти все значения уникальны")
        if id_like_ratio >= 0.75:
            score += 0.2
            reasons.append("значения похожи на технические идентификаторы")
        if score < 0.72:
            return None
        return FieldDetection("id_like", min(0.93, score), "; ".join(reasons))

    def _detect_category(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        unique_count = len(set(values))
        unique_ratio = unique_count / max(len(values), 1)
        if not self._name_has_token(name_tokens, CATEGORY_NAME_TOKENS):
            return None
        if unique_count <= 30 or unique_ratio <= 0.45:
            return FieldDetection(
                detected_type="category",
                confidence=0.86,
                reason="Название колонки указывает на категорию, а кардинальность значений невысока.",
            )
        return None

    def _detect_free_text(self, column_name: str, name_tokens: set[str], values: list[str]) -> FieldDetection | None:
        average_length = sum(len(value) for value in values) / max(len(values), 1)
        long_text_ratio = self._match_ratio(values, lambda value: len(value.split()) >= 4 or len(value) >= 30)
        if self._name_has_token(name_tokens, TEXT_NAME_TOKENS) and (long_text_ratio >= 0.35 or average_length >= 24):
            return FieldDetection(
                detected_type="text",
                confidence=0.84,
                reason="Название и длина значений похожи на свободный текст.",
            )
        return None

    def _detect_boolean(self, column_name: str, values: list[str]) -> FieldDetection | None:
        normalized = {value.lower() for value in values}
        if normalized.issubset(BOOLEAN_TRUE | BOOLEAN_FALSE):
            return FieldDetection(
                detected_type="boolean",
                confidence=0.9,
                reason="Все значения принадлежат булевому набору true/false/yes/no/0/1.",
            )
        return None

    def _detect_number(self, column_name: str, values: list[str]) -> FieldDetection | None:
        if self._match_ratio(values, lambda value: bool(NUMBER_PATTERN.fullmatch(value.replace(" ", "")))) < 0.95:
            return None
        if any(token in column_name for token in ("price", "amount", "sum", "total", "qty", "quantity", "count")):
            return FieldDetection(
                detected_type="number",
                confidence=0.9,
                reason="Название и значения указывают на числовое поле.",
            )
        return FieldDetection(
            detected_type="number",
            confidence=0.82,
            reason="Значения выглядят как числа.",
        )

    @staticmethod
    def _match_ratio(values: list[str], predicate) -> float:
        if not values:
            return 0.0
        matches = sum(1 for value in values if predicate(value))
        return matches / len(values)

    @staticmethod
    def _looks_like_phone(value: str) -> bool:
        digits = [char for char in value if char.isdigit()]
        return 7 <= len(digits) <= 15 and bool(PHONE_PATTERN.fullmatch(value.strip()))

    @staticmethod
    def _looks_like_full_name(value: str) -> bool:
        tokens = FULL_NAME_PATTERN.findall(value)
        return 2 <= len(tokens) <= 4 and all(len(token) >= 2 for token in tokens)

    @staticmethod
    def _looks_like_single_name(value: str) -> bool:
        tokens = FULL_NAME_PATTERN.findall(value)
        return len(tokens) == 1 and len(tokens[0]) >= 2

    @staticmethod
    def _looks_like_address(value: str) -> bool:
        lowered = value.lower()
        if any(marker in lowered for marker in ADDRESS_MARKERS):
            return True
        return bool(re.search(r"\d", value)) and len(value.split()) >= 3

    @staticmethod
    def _looks_like_city(value: str) -> bool:
        lowered = value.lower().strip()
        if lowered in CITY_NAMES:
            return True
        if re.search(r"\d", value):
            return False
        words = [word for word in re.split(r"[\s-]+", value.strip()) if word]
        return 1 <= len(words) <= 3 and all(word[:1].isalpha() for word in words) and len(value) <= 40

    @staticmethod
    def _looks_like_vehicle_plate(value: str) -> bool:
        normalized = value.replace(" ", "").upper()
        return any(pattern.fullmatch(normalized) for pattern in VEHICLE_PLATE_PATTERNS)

    def _date_ratios(self, values: list[str]) -> tuple[float, float]:
        if not values:
            return 0.0, 0.0

        date_like = 0
        datetime_like = 0
        for value in values:
            parsed_kind = self._parse_date_value(value)
            if parsed_kind is None:
                continue
            date_like += 1
            if parsed_kind == "datetime":
                datetime_like += 1

        return date_like / len(values), datetime_like / len(values)

    @staticmethod
    def _parse_date_value(value: str) -> str | None:
        normalized = value.strip()
        if not normalized:
            return None

        if TIMESTAMP_PATTERN.fullmatch(normalized):
            try:
                epoch_value = int(normalized)
                if len(normalized) == 13:
                    epoch_value = epoch_value / 1000
                parsed = datetime.fromtimestamp(epoch_value, UTC)
                if 1970 <= parsed.year <= 2100:
                    return "datetime"
            except (OverflowError, OSError, ValueError):
                return None

        for fmt in DATE_FORMATS:
            try:
                datetime.strptime(normalized, fmt)
                return "datetime" if any(token in fmt for token in ("H", "M", "S")) else "date"
            except ValueError:
                continue

        try:
            datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            return "datetime" if "T" in normalized or ":" in normalized else "date"
        except ValueError:
            return None

    @staticmethod
    def _extract_name_tokens(column_name: str) -> set[str]:
        normalized_name = re.sub(r"([a-zа-яё])([A-ZА-ЯЁ])", r"\1_\2", column_name)
        tokens = {
            token
            for token in re.split(r"[^a-zA-Zа-яА-ЯЁё0-9]+", normalized_name.lower())
            if token
        }
        if column_name:
            tokens.add(column_name.lower())
        if normalized_name:
            tokens.add(normalized_name.lower())
        return tokens

    @staticmethod
    def _name_has_token(name_tokens: set[str], candidates: set[str]) -> bool:
        return bool(name_tokens & candidates)

    @staticmethod
    def _looks_like_identifier(value: str) -> bool:
        normalized = value.strip()
        if len(normalized) < 3:
            return False
        if INTEGER_PATTERN.fullmatch(normalized):
            return True
        return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{2,}", normalized))
