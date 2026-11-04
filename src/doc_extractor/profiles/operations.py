"""Allowlisted data operations driven by validated YAML, not executable YAML code."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ..models import ExtractionResult, Issue, RecordSet, Value
from .loader import Profile

# Integer part with optional grouping and fraction, or a bare fraction such as ".02"
# (some statements print amounts below 1 without the leading zero: "-.02", ".00").
_NUMBER_PATTERN = re.compile(r"^[+-]?(?:(?:\d{1,3}(?:[., ]\d{3})+|\d+)(?:[.,]\d+)?|[.,]\d+)$")


def find_period(text: str, spec: dict[str, str]) -> tuple[date, date]:
    """Read a statement period, e.g. ``DESDE: 2025/12/31 HASTA: 2026/03/31``.

    Each date is the first word after its label in the page text. Labels, not regular
    expressions, keep profiles declarative.
    """
    found = []
    for label in (spec["start_label"], spec["end_label"]):
        position = text.find(label)
        words = text[position + len(label) :].split() if position >= 0 else []
        if not words:
            raise ValueError(f"Statement period label {label!r} not found")
        found.append(datetime.strptime(words[0], spec["format"]).date())
    start, end = found
    if end < start:
        raise ValueError("Statement period ends before it starts")
    return start, end


def _date_in_period(raw: str, fmt: str, period: tuple[date, date] | None) -> date:
    """Complete a day-month date with the only year that places it inside the period."""
    if period is None:
        raise ValueError("Statement period not found; cannot infer the year")
    start, end = period
    parsed, inside = False, []
    for year in range(start.year, end.year + 1):
        try:  # add the year before parsing so that 29 February works in leap years
            candidate = datetime.strptime(f"{raw} {year}", f"{fmt} %Y").date()
        except ValueError:
            continue
        parsed = True
        if start <= candidate <= end:
            inside.append(candidate)
    if not parsed:
        raise ValueError("Date does not match the format")
    if not inside:
        raise ValueError("Date lies outside the statement period")
    if len(inside) > 1:
        raise ValueError("Year is ambiguous: the period spans more than a year")
    return inside[0]


def _normalize(
    raw: str | None, settings: dict[str, Any], period: tuple[date, date] | None = None
) -> tuple[str | None, str | None]:
    if raw is None or not raw.strip():
        return None, None
    value_type = settings["type"]
    if value_type == "date":
        if "year_from_period" in settings:
            return _date_in_period(raw.strip(), settings["format"], period).isoformat(), "date"
        value = datetime.strptime(raw.strip(), settings["format"]).date().isoformat()
        return value, "date"
    if value_type == "decimal":
        dec = settings.get("decimal_separator", ".")
        thou = settings.get("thousands_separator", ",")
        text = raw.strip().replace("\u00a0", " ").replace("\u202f", " ")
        # Never silently discard digits, punctuation, or unsupported currency units.
        if not _NUMBER_PATTERN.fullmatch(text):
            raise ValueError("Invalid decimal syntax")
        if text.count(dec) > 1:
            raise ValueError("More than one decimal separator")
        whole, dot, fraction = text.partition(dec)
        if thou in fraction or (dot and len(fraction) == 0):
            raise ValueError("Invalid decimal grouping")
        groups = whole.lstrip("+-").split(thou)
        if len(groups) > 1 and (
            not 1 <= len(groups[0]) <= 3 or not all(len(g) == 3 for g in groups[1:])
        ):
            raise ValueError("Invalid thousands grouping")
        number = whole.replace(thou, "") + ("." + fraction if dot else "")
        normalized = format(Decimal(number), "f")
        return normalized, "decimal"
    raise ValueError("Unsupported normalization type")


def _periods(
    parsers: dict[str, dict[str, Any]], result: ExtractionResult
) -> dict[int, tuple[date, date]]:
    """Find each requested statement period once; report a missing one a single time."""
    text = "\n".join(page.text for page in result.pages)
    periods: dict[int, tuple[date, date]] = {}
    for settings in parsers.values():
        spec = settings.get("year_from_period")
        if not spec:
            continue
        try:
            periods[id(settings)] = find_period(text, spec)
        except ValueError as exc:
            result.issues.append(Issue("PERIOD_NOT_FOUND", f"{exc}; dates keep their raw value."))
    return periods


def apply_mapping(profile: Profile, result: ExtractionResult) -> None:
    """Map known table headers to records with preserved per-field cell provenance."""
    mappings = [s for s in profile.pipeline if s["op"] == "table.map_columns"]
    if not mappings:
        return
    for step in mappings:
        params = step["params"]
        column_mapping: dict[str, str] = params["column_mapping"]
        parsers: dict[str, dict[str, Any]] = params.get("optional_parsing", {})
        periods = _periods(parsers, result)
        matched_tables = 0
        for table in result.tables:
            if not table.cells:
                continue
            header = [c.text.strip() if c.text else "" for c in table.cells[0]]
            if len(set(header)) != len(header) or any(k not in header for k in column_mapping):
                continue
            matched_tables += 1
            columns = {name: header.index(name) for name in column_mapping}
            records: list[dict[str, Value]] = []
            for row in table.cells[1:]:
                if not any(c.text and c.text.strip() for c in row):
                    continue
                item: dict[str, Value] = {}
                for source_header, output_field in column_mapping.items():
                    index = columns[source_header]
                    if index >= len(row):
                        result.issues.append(
                            Issue(
                                "INCOMPLETE_ROW",
                                "A record is missing a mapped source cell.",
                                location=table.source,
                            )
                        )
                        continue
                    cell = row[index]
                    raw = cell.text
                    normalized, value_type = None, None
                    parsing = parsers.get(output_field) or parsers.get(source_header)
                    if parsing and raw is not None and raw.strip():
                        try:
                            normalized, value_type = _normalize(
                                raw, parsing, periods.get(id(parsing))
                            )
                        except (ValueError, InvalidOperation) as exc:
                            result.issues.append(
                                Issue(
                                    "NORMALIZATION_FAILED",
                                    f"Cannot normalize field {output_field!r} ({type(exc).__name__}); raw cell preserved.",
                                    location=cell.source,
                                )
                            )
                    item[output_field] = Value(
                        raw=raw,
                        normalized=normalized,
                        normalized_type=value_type,
                        source=cell.source,
                        normalization_requested=bool(parsing),
                    )
                if len(item) == len(column_mapping):
                    records.append(item)
            result.record_sets.append(
                RecordSet(
                    id=f"records_{len(result.record_sets) + 1}",
                    records=records,
                    source_table_id=table.id,
                )
            )
        if not matched_tables:
            result.issues.append(
                Issue(
                    "LAYOUT_MISMATCH",
                    "No table contains all required mapped column headers.",
                )
            )
