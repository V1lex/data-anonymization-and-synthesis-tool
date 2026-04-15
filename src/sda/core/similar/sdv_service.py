import re
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from sdv.metadata import Metadata
from sdv.single_table import GaussianCopulaSynthesizer

SDV_TABLE_NAME = "source_table"
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)
TRUE_VALUES = {"true", "1", "yes", "y", "да"}
FALSE_VALUES = {"false", "0", "no", "n", "нет"}
ID_COLUMN_PATTERN = re.compile(r"(^id$|_id$|uuid|guid|reference|ref)", re.IGNORECASE)
INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
FLOAT_PATTERN = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    display_type: str
    sdtype: str
    datetime_format: str | None = None
    boolean_true_value: str | None = None
    boolean_false_value: str | None = None
    numerical_kind: str | None = None
    id_strategy: str | None = None
    sequence_start: int | None = None
    sequence_step: int | None = None
    sequence_width: int | None = None
    sequence_prefix: str | None = None
    sequence_suffix: str | None = None


class SdvSimilarService:
    """Анализирует single-table CSV и генерирует похожие данные через SDV."""

    def analyze(
        self,
        *,
        rows: list[dict[str, str]],
        header: list[str],
        preview_rows_limit: int,
    ) -> dict[str, Any]:
        dataframe, column_specs = self._build_typed_dataframe(rows=rows, header=header)
        metadata = self._build_metadata(dataframe=dataframe, column_specs=column_specs)
        column_profiles = self._build_column_profiles(
            rows=rows,
            header=header,
            column_specs=column_specs,
        )
        warnings_list = self._build_analysis_warnings(rows=rows, columns=column_profiles)
        return {
            "metadata": metadata.to_dict(),
            "column_specs": {
                column_name: asdict(spec)
                for column_name, spec in column_specs.items()
            },
            "columns": column_profiles,
            "preview_rows": rows[:preview_rows_limit],
            "summary": self._build_summary(
                row_count=len(rows),
                column_profiles=column_profiles,
                metadata=metadata,
            ),
            "warnings": warnings_list,
        }

    def synthesize(
        self,
        *,
        rows: list[dict[str, str]],
        header: list[str],
        metadata_payload: dict[str, Any],
        column_specs_payload: dict[str, dict[str, Any]],
        target_rows: int,
    ) -> dict[str, Any]:
        dataframe, column_specs = self._build_typed_dataframe(
            rows=rows,
            header=header,
            stored_specs=column_specs_payload,
        )
        metadata = Metadata.load_from_dict(metadata_payload)
        warnings_list: list[str] = []

        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.filterwarnings(
                "ignore",
                message="We strongly recommend saving the metadata using 'save_to_json'.*",
            )
            synthesizer = GaussianCopulaSynthesizer(metadata)
            synthesizer.fit(dataframe)
            sampled = synthesizer.sample(num_rows=target_rows)

        for item in captured_warnings:
            message = str(item.message).strip()
            if message:
                warnings_list.append(message)

        sampled_rows = self._format_sampled_dataframe(
            dataframe=sampled,
            header=header,
            column_specs=column_specs,
        )
        return {
            "rows": sampled_rows,
            "warnings": warnings_list[:10],
        }

    def _build_metadata(
        self,
        *,
        dataframe: pd.DataFrame,
        column_specs: dict[str, ColumnSpec],
    ) -> Metadata:
        metadata = Metadata.detect_from_dataframes({SDV_TABLE_NAME: dataframe})

        for spec in column_specs.values():
            update_kwargs: dict[str, Any] = {"sdtype": spec.sdtype}
            if spec.datetime_format is not None:
                update_kwargs["datetime_format"] = spec.datetime_format
            metadata.update_column(spec.name, table_name=SDV_TABLE_NAME, **update_kwargs)

        primary_key = (
            metadata.to_dict()
            .get("tables", {})
            .get(SDV_TABLE_NAME, {})
            .get("primary_key")
        )
        primary_key_spec = column_specs.get(primary_key) if primary_key is not None else None
        if primary_key is not None and (primary_key_spec is None or primary_key_spec.sdtype != "id"):
            metadata.remove_primary_key(table_name=SDV_TABLE_NAME)

        return metadata

    def _build_typed_dataframe(
        self,
        *,
        rows: list[dict[str, str]],
        header: list[str],
        stored_specs: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[pd.DataFrame, dict[str, ColumnSpec]]:
        series_map: dict[str, pd.Series] = {}
        column_specs: dict[str, ColumnSpec] = {}

        for column_name in header:
            values = [row.get(column_name, "") for row in rows]
            spec = (
                self._load_column_spec(stored_specs[column_name])
                if stored_specs and column_name in stored_specs
                else self._infer_column_spec(column_name=column_name, values=values)
            )
            series_map[column_name] = self._cast_series(values=values, spec=spec)
            column_specs[column_name] = spec

        return pd.DataFrame(series_map, columns=header), column_specs

    def _infer_column_spec(self, *, column_name: str, values: list[str]) -> ColumnSpec:
        non_empty = [value.strip() for value in values if value is not None and value.strip()]
        if not non_empty:
            return ColumnSpec(
                name=column_name,
                display_type="text",
                sdtype="categorical",
            )

        boolean_tokens = self._detect_boolean_tokens(non_empty)
        if boolean_tokens is not None:
            return ColumnSpec(
                name=column_name,
                display_type="boolean",
                sdtype="boolean",
                boolean_true_value=boolean_tokens[0],
                boolean_false_value=boolean_tokens[1],
            )

        datetime_format = self._detect_datetime_format(non_empty)
        if datetime_format is not None:
            return ColumnSpec(
                name=column_name,
                display_type="datetime",
                sdtype="datetime",
                datetime_format=datetime_format,
            )

        if self._looks_like_identifier(column_name=column_name, values=non_empty):
            auto_increment_info = self._detect_auto_increment_pattern(non_empty)
            return ColumnSpec(
                name=column_name,
                display_type="id",
                sdtype="id",
                id_strategy="auto_increment" if auto_increment_info is not None else None,
                sequence_start=auto_increment_info["start"] if auto_increment_info is not None else None,
                sequence_step=auto_increment_info["step"] if auto_increment_info is not None else None,
                sequence_width=auto_increment_info["width"] if auto_increment_info is not None else None,
                sequence_prefix=auto_increment_info["prefix"] if auto_increment_info is not None else None,
                sequence_suffix=auto_increment_info["suffix"] if auto_increment_info is not None else None,
            )

        numerical_kind = self._detect_numerical_kind(non_empty)
        if numerical_kind is not None:
            return ColumnSpec(
                name=column_name,
                display_type="numerical",
                sdtype="numerical",
                numerical_kind=numerical_kind,
            )

        unique_ratio = len(set(non_empty)) / max(len(non_empty), 1)
        display_type = "category" if unique_ratio <= 0.35 or len(set(non_empty)) <= 20 else "text"
        return ColumnSpec(
            name=column_name,
            display_type=display_type,
            sdtype="categorical",
        )

    def _cast_series(self, *, values: list[str], spec: ColumnSpec) -> pd.Series:
        normalized_values = [
            None if value is None or not str(value).strip() else str(value).strip()
            for value in values
        ]

        if spec.sdtype == "boolean":
            boolean_map = {
                value: True
                for value in TRUE_VALUES
            }
            boolean_map.update({value: False for value in FALSE_VALUES})
            return pd.Series(
                [
                    None if value is None else boolean_map[str(value).strip().lower()]
                    for value in normalized_values
                ],
                dtype="boolean",
            )

        if spec.sdtype == "datetime":
            return pd.to_datetime(
                normalized_values,
                format=spec.datetime_format,
                errors="coerce",
            )

        if spec.sdtype == "numerical":
            numeric_values = [
                None if value is None else value.replace(",", ".")
                for value in normalized_values
            ]
            if spec.numerical_kind == "int":
                numeric_series = pd.to_numeric(numeric_values, errors="coerce")
                return numeric_series.round().astype("Int64")
            return pd.to_numeric(numeric_values, errors="coerce")

        return pd.Series(normalized_values, dtype="object")

    def _build_column_profiles(
        self,
        *,
        rows: list[dict[str, str]],
        header: list[str],
        column_specs: dict[str, ColumnSpec],
    ) -> list[dict[str, Any]]:
        column_profiles: list[dict[str, Any]] = []
        total_rows = len(rows) or 1

        for column_name in header:
            values = [row.get(column_name, "") for row in rows]
            non_empty = [value.strip() for value in values if value is not None and value.strip()]
            unique_values = len(set(non_empty))
            column_profiles.append(
                {
                    "name": column_name,
                    "inferred_type": column_specs[column_name].display_type,
                    "null_ratio": round(1.0 - (len(non_empty) / total_rows), 4),
                    "unique_ratio": round(unique_values / max(len(non_empty), 1), 4),
                    "sample_values": non_empty[:5],
                }
            )

        return column_profiles

    def _build_summary(
        self,
        *,
        row_count: int,
        column_profiles: list[dict[str, Any]],
        metadata: Metadata,
    ) -> list[str]:
        counts: dict[str, int] = {}
        for column in column_profiles:
            inferred_type = str(column["inferred_type"])
            counts[inferred_type] = counts.get(inferred_type, 0) + 1

        summary = [
            f"Найдено колонок: {len(column_profiles)}",
            f"Строк во входном CSV: {row_count}",
        ]
        for key in ("id", "numerical", "datetime", "boolean", "category", "text"):
            if counts.get(key):
                summary.append(f"{key}: {counts[key]}")

        primary_key = (
            metadata.to_dict()
            .get("tables", {})
            .get(SDV_TABLE_NAME, {})
            .get("primary_key")
        )
        if primary_key:
            summary.append(f"Первичный ключ SDV: {primary_key}")

        return summary[:10]

    def _build_analysis_warnings(
        self,
        *,
        rows: list[dict[str, str]],
        columns: list[dict[str, Any]],
    ) -> list[str]:
        warnings_list: list[str] = []
        if len(rows) < 10:
            warnings_list.append(
                "Во входном CSV мало строк. Похожий датасет будет менее стабильным."
            )

        high_cardinality_columns = [
            column["name"]
            for column in columns
            if column["inferred_type"] in {"text", "category"} and column["unique_ratio"] >= 0.95
        ]
        if high_cardinality_columns:
            joined = ", ".join(high_cardinality_columns[:3])
            warnings_list.append(
                f"Колонки с очень высокой уникальностью могут воспроизводиться хуже: {joined}."
            )

        return warnings_list[:10]

    def _format_sampled_dataframe(
        self,
        *,
        dataframe: pd.DataFrame,
        header: list[str],
        column_specs: dict[str, ColumnSpec],
    ) -> list[dict[str, str]]:
        formatted_rows: list[dict[str, str]] = []
        for row_index, (_, record) in enumerate(dataframe[header].iterrows()):
            row: dict[str, str] = {}
            for column_name in header:
                spec = column_specs[column_name]
                if spec.id_strategy == "auto_increment":
                    row[column_name] = self._build_auto_increment_id(
                        row_index=row_index,
                        spec=spec,
                    )
                else:
                    row[column_name] = self._format_value(
                        value=record[column_name],
                        spec=spec,
                    )
            formatted_rows.append(row)
        return formatted_rows

    def _format_value(self, *, value: Any, spec: ColumnSpec) -> str:
        if pd.isna(value):
            return ""

        if spec.sdtype == "datetime":
            timestamp = pd.to_datetime(value, errors="coerce")
            if pd.isna(timestamp):
                return ""
            if spec.datetime_format:
                return timestamp.strftime(spec.datetime_format)
            return timestamp.isoformat()

        if spec.sdtype == "boolean":
            return spec.boolean_true_value if bool(value) else spec.boolean_false_value

        if spec.sdtype == "numerical":
            numeric_value = float(value)
            if spec.numerical_kind == "int":
                return str(int(round(numeric_value)))
            formatted = f"{numeric_value:.6f}".rstrip("0").rstrip(".")
            return formatted or "0"

        return str(value)

    @staticmethod
    def _build_auto_increment_id(*, row_index: int, spec: ColumnSpec) -> str:
        start = spec.sequence_start if spec.sequence_start is not None else 1
        step = spec.sequence_step if spec.sequence_step is not None else 1
        prefix = spec.sequence_prefix or ""
        suffix = spec.sequence_suffix or ""
        width = spec.sequence_width if spec.sequence_width is not None else 0

        value = start + (row_index * step)
        number_part = str(value).zfill(width) if width > 0 else str(value)
        return f"{prefix}{number_part}{suffix}"

    @staticmethod
    def _load_column_spec(payload: dict[str, Any]) -> ColumnSpec:
        return ColumnSpec(
            name=str(payload["name"]),
            display_type=str(payload["display_type"]),
            sdtype=str(payload["sdtype"]),
            datetime_format=payload.get("datetime_format"),
            boolean_true_value=payload.get("boolean_true_value"),
            boolean_false_value=payload.get("boolean_false_value"),
            numerical_kind=payload.get("numerical_kind"),
            id_strategy=payload.get("id_strategy"),
            sequence_start=payload.get("sequence_start"),
            sequence_step=payload.get("sequence_step"),
            sequence_width=payload.get("sequence_width"),
            sequence_prefix=payload.get("sequence_prefix"),
            sequence_suffix=payload.get("sequence_suffix"),
        )

    @staticmethod
    def _detect_boolean_tokens(values: list[str]) -> tuple[str, str] | None:
        normalized = {value.strip().lower() for value in values}
        if not normalized:
            return None
        if normalized.issubset({"1", "0"}):
            return "1", "0"
        if normalized.issubset({"yes", "no"}):
            return "yes", "no"
        if normalized.issubset({"да", "нет"}):
            return "да", "нет"
        if normalized.issubset(TRUE_VALUES | FALSE_VALUES):
            return "true", "false"
        return None

    @staticmethod
    def _detect_datetime_format(values: list[str]) -> str | None:
        for fmt in DATE_FORMATS:
            try:
                for value in values:
                    datetime.strptime(value, fmt)
            except ValueError:
                continue
            return fmt
        return None

    @staticmethod
    def _detect_numerical_kind(values: list[str]) -> str | None:
        has_float = False
        for value in values:
            normalized = value.replace(" ", "")
            if INTEGER_PATTERN.fullmatch(normalized):
                if len(normalized.lstrip("+-")) > 1 and normalized.lstrip("+-").startswith("0"):
                    return None
                continue

            if FLOAT_PATTERN.fullmatch(normalized):
                has_float = True
                continue

            return None

        return "float" if has_float else "int"

    @staticmethod
    def _looks_like_identifier(*, column_name: str, values: list[str]) -> bool:
        if not ID_COLUMN_PATTERN.search(column_name):
            return False
        normalized_values = [value.strip() for value in values if value.strip()]
        return len(set(normalized_values)) == len(normalized_values)

    @staticmethod
    def _detect_auto_increment_pattern(values: list[str]) -> dict[str, int | str] | None:
        parsed_values: list[tuple[str, int, int, str]] = []
        for raw_value in values:
            match = re.fullmatch(r"(.*?)(\d+)(.*?)", raw_value)
            if match is None:
                return None

            prefix, digits, suffix = match.groups()
            parsed_values.append((prefix, int(digits), len(digits), suffix))

        prefixes = {item[0] for item in parsed_values}
        widths = {item[2] for item in parsed_values}
        suffixes = {item[3] for item in parsed_values}
        numbers = [item[1] for item in parsed_values]

        if len(prefixes) != 1 or len(suffixes) != 1 or len(set(numbers)) != len(numbers):
            return None
        if len(numbers) < 2:
            step = 1
        else:
            step = numbers[1] - numbers[0]
            if step <= 0:
                return None
            if any((numbers[index + 1] - numbers[index]) != step for index in range(len(numbers) - 1)):
                return None

        return {
            "prefix": parsed_values[0][0],
            "start": numbers[0],
            "step": step,
            "width": parsed_values[0][2] if len(widths) == 1 else 0,
            "suffix": parsed_values[0][3],
        }
