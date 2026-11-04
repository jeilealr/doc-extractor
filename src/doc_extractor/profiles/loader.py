"""Safe, bounded YAML profiles; optional trusted installed-package entry points."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from importlib import metadata, resources
from pathlib import Path
from typing import Any

import yaml

from ..errors import ProfileError
from ..readers.header_table import PARAMS as HEADER_TABLE_PARAMS
from ..readers.header_table import validate_header_table_settings
from ..readers.pdf_reader import validate_table_settings

SCHEMA_VERSION = 1
MAX_YAML_BYTES = 128 * 1024
ALLOWED_OPS = {
    "csv.collect_raw_rows",
    "pdf.collect_text_blocks",
    "pdf.detect_tables",
    "pdf.table_from_header",
    "table.map_columns",
}
COMMON_KEYS = {
    "profile_schema_version",
    "id",
    "version",
    "kind",
    "format",
    "purpose",
    "description",
    "match",
    "pipeline",
    "output",
    "validation",
    "status",
}


@dataclass(frozen=True)
class Profile:
    id: str
    version: str
    kind: str
    file_format: str
    pipeline: tuple[dict[str, Any], ...]
    match: dict[str, list[str]]
    sha256: str
    source: str


def _check_safe_tree(value: Any, seen: set[int] | None = None, depth: int = 0) -> int:
    """Reject cyclic/abnormally nested YAML aliases and overly large structures."""
    if depth > 16:
        raise ProfileError("YAML nesting exceeds the safety limit")
    if isinstance(value, (str, int, float, bool, type(None))):
        return 1
    if not isinstance(value, (list, dict)):
        raise ProfileError("YAML must contain only standard mappings, sequences, and scalars")
    if seen is None:
        seen = set()
    if id(value) in seen:
        raise ProfileError("Recursive or reused YAML collection aliases are not supported")
    # Track all visited collection objects, not just active ancestors: a YAML
    # alias reused in two branches is rejected as well as an actual cycle.
    seen.add(id(value))
    children = list(value.items()) if isinstance(value, dict) else value
    total = 1
    if isinstance(value, dict):
        for key, item in children:
            total += _check_safe_tree(key, seen, depth + 1)
            total += _check_safe_tree(item, seen, depth + 1)
    else:
        for item in children:
            total += _check_safe_tree(item, seen, depth + 1)
    if total > 2000:
        raise ProfileError("YAML contains too many elements")
    return total


def _string_map(obj: Any, *, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(obj, dict) or not all(isinstance(k, str) for k in obj):
        raise ProfileError(f"{label} must be a mapping with string keys")
    unknown = set(obj) - keys
    if unknown:
        raise ProfileError(f"Unknown keys in {label}: {', '.join(sorted(unknown))}")
    return obj


def _operation(raw: Any, fmt: str, previous_aliases: set[str]) -> dict[str, Any]:
    op = _string_map(raw, keys={"op", "as", "input", "params"}, label="pipeline operation")
    name = op.get("op")
    if name not in ALLOWED_OPS:
        raise ProfileError(f"Unsupported operation: {name!r}")
    if name.startswith("pdf.") and fmt != "pdf" or name.startswith("csv.") and fmt != "csv":
        raise ProfileError(f"Operation {name} is not compatible with {fmt}")
    alias = op.get("as")
    if not isinstance(alias, str) or not alias.isidentifier() or alias in previous_aliases:
        raise ProfileError("Each pipeline operation needs a unique identifier in 'as'")
    previous_aliases.add(alias)
    if "input" in op and (not isinstance(op["input"], str) or op["input"] not in previous_aliases):
        raise ProfileError("Operation input must reference a previous 'as' alias")
    if op.get("input") == alias:
        raise ProfileError("Operation cannot use itself as input")
    params = _string_map(
        op.get("params", {}),
        keys={
            "encoding",
            "delimiter",
            "infer_types",
            "keep_raw_cell_strings",
            "include_row_and_column",
            "first_row_header",
            "preserve_raw",
            "include_page_and_bbox",
            "vertical_strategy",
            "horizontal_strategy",
            "preserve_raw_cells",
            "include_cell_bbox",
            "min_words_vertical",
            "min_words_horizontal",
            "snap_tolerance",
            "join_tolerance",
            "intersection_tolerance",
            "text_x_tolerance",
            "text_y_tolerance",
            "column_mapping",
            "optional_parsing",
            *HEADER_TABLE_PARAMS,
        },
        label="operation params",
    )
    allowed_by_op = {
        "csv.collect_raw_rows": {
            "encoding",
            "delimiter",
            "infer_types",
            "keep_raw_cell_strings",
            "include_row_and_column",
            "first_row_header",
        },
        "pdf.collect_text_blocks": {"preserve_raw", "include_page_and_bbox"},
        "pdf.detect_tables": {
            "vertical_strategy",
            "horizontal_strategy",
            "preserve_raw_cells",
            "include_cell_bbox",
            "min_words_vertical",
            "min_words_horizontal",
            "snap_tolerance",
            "join_tolerance",
            "intersection_tolerance",
            "text_x_tolerance",
            "text_y_tolerance",
        },
        "pdf.table_from_header": set(HEADER_TABLE_PARAMS),
        "table.map_columns": {"column_mapping", "optional_parsing"},
    }
    if set(params) - allowed_by_op[name]:
        raise ProfileError(f"Unsupported parameter(s) for {name}")
    for key in (
        "infer_types",
        "keep_raw_cell_strings",
        "include_row_and_column",
        "preserve_raw",
        "include_page_and_bbox",
        "preserve_raw_cells",
        "include_cell_bbox",
    ):
        if key in params and params[key] is not (key != "infer_types"):
            raise ProfileError(f"{key} cannot disable the source-fidelity contract")
    if name == "pdf.detect_tables":
        validate_table_settings(
            {
                k: v
                for k, v in params.items()
                if k not in {"preserve_raw_cells", "include_cell_bbox"}
            }
        )
    if name == "pdf.table_from_header":
        validate_header_table_settings(params)
    if name == "csv.collect_raw_rows":
        if params.get("encoding", "utf-8-sig") not in {
            "detect_or_require_override",
            "utf-8",
            "utf-8-sig",
            "cp1252",
            "latin-1",
            "iso-8859-1",
        }:
            raise ProfileError("Unsupported CSV encoding in YAML profile")
        if params.get("delimiter", ",") not in {"detect_or_require_override", ",", ";", "\t", "|"}:
            raise ProfileError("Unsupported CSV delimiter in YAML profile")
        if "first_row_header" in params and not isinstance(params["first_row_header"], bool):
            raise ProfileError("first_row_header must be a boolean")
    if name == "table.map_columns":
        mapping = params.get("column_mapping")
        if (
            not isinstance(mapping, dict)
            or not mapping
            or not all(
                isinstance(k, str) and k and isinstance(v, str) and v for k, v in mapping.items()
            )
            or len(set(mapping.values())) != len(mapping)
        ):
            raise ProfileError(
                "column_mapping must map distinct source columns to distinct field names"
            )
        parsing = params.get("optional_parsing", {})
        if not isinstance(parsing, dict) or not all(isinstance(k, str) for k in parsing):
            raise ProfileError("optional_parsing must be a mapping")
        for field, settings in parsing.items():
            if field not in set(mapping.values()) | set(mapping):
                raise ProfileError("optional_parsing references an unknown field")
            settings = _string_map(
                settings,
                keys={
                    "type",
                    "format",
                    "decimal_separator",
                    "thousands_separator",
                    "year_from_period",
                },
                label="parsing",
            )
            if settings.get("type") not in {"date", "decimal"}:
                raise ProfileError("Only date and decimal normalization are supported")
            if settings["type"] == "date":
                _date_settings(settings)
            else:
                dec = settings.get("decimal_separator", ".")
                sep = settings.get("thousands_separator", ",")
                if not all(isinstance(x, str) and len(x) == 1 for x in (dec, sep)) or dec == sep:
                    raise ProfileError("Invalid decimal separators")
    return op


DATE_FORMATS_WITH_YEAR = {"%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d.%m.%Y"}
DATE_FORMATS_WITHOUT_YEAR = {"%d/%m", "%d.%m.", "%d.%m"}


def _date_settings(settings: dict[str, Any]) -> None:
    fmt = settings.get("format")
    period = settings.get("year_from_period")
    if fmt in DATE_FORMATS_WITHOUT_YEAR:
        if period is None:
            raise ProfileError(f"Date format {fmt!r} has no year: add year_from_period")
        period = _string_map(
            period, keys={"start_label", "end_label", "format"}, label="year_from_period"
        )
        if not all(
            isinstance(period.get(k), str) and period[k].strip() and len(period[k]) <= 100
            for k in ("start_label", "end_label")
        ):
            raise ProfileError("year_from_period needs non-empty start_label and end_label")
        if period.get("format") not in DATE_FORMATS_WITH_YEAR:
            raise ProfileError("Unsupported year_from_period date format")
    elif fmt in DATE_FORMATS_WITH_YEAR:
        if period is not None:
            raise ProfileError("year_from_period only applies to date formats without a year")
    else:
        raise ProfileError("Unsupported date format")


def from_bytes(data: bytes, *, source: str) -> Profile:
    if len(data) > MAX_YAML_BYTES:
        raise ProfileError("YAML profile exceeds 128 KiB")
    try:
        parsed = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ProfileError("Malformed YAML profile") from exc
    _check_safe_tree(parsed)
    status = parsed.get("status") if isinstance(parsed, dict) else None
    if isinstance(status, str) and status.startswith("design"):
        raise ProfileError(
            f"This is a design-only profile sketch (status: {status}); it cannot be run. "
            "See docs/design/bank-profiles/README.md"
        )
    body = _string_map(parsed, keys=COMMON_KEYS, label="profile")
    if body.get("profile_schema_version") != SCHEMA_VERSION:
        raise ProfileError("Unsupported profile_schema_version; expected 1")
    pid = body.get("id")
    if (
        not isinstance(pid, str)
        or not 3 <= len(pid) <= 128
        or not all(x.isalnum() or x in ".-_" for x in pid)
    ):
        raise ProfileError("Invalid profile ID")
    version = body.get("version", "1.0.0")
    if not isinstance(version, str) or not 1 <= len(version) <= 30:
        raise ProfileError("Invalid profile version")
    fmt, kind = body.get("format"), body.get("kind")
    if fmt not in {"pdf", "csv"} or kind not in {"preset", "source"}:
        raise ProfileError("Profile kind must be preset/source and format must be pdf/csv")
    if body.get("status", "ready") != "ready":
        raise ProfileError("Design-only profile is not runnable")
    match = _string_map(
        body.get("match", {}), keys={"required_text", "required_headers"}, label="match"
    )
    if kind == "source" and not match:
        raise ProfileError("Source profiles require a conservative fingerprint")
    for key, value in match.items():
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(x, str) and x.strip() and len(x) <= 250 for x in value)
        ):
            raise ProfileError(f"{key} must be a nonempty list of short strings")
    if kind == "source":
        unique_signatures = sum(len(set(value)) for value in match.values())
        if unique_signatures < 2:
            raise ProfileError("Source profile fingerprint requires at least two distinct anchors")
    pipeline = body.get("pipeline")
    if not isinstance(pipeline, list) or not pipeline or len(pipeline) > 12:
        raise ProfileError("Pipeline must contain 1 to 12 supported operations")
    aliases: set[str] = set()
    steps = [_operation(step, fmt, aliases) for step in pipeline]
    alias_to_op = {step["as"]: step["op"] for step in steps}
    for step in steps:
        if step["op"] == "table.map_columns":
            if alias_to_op.get(step.get("input")) not in {
                "csv.collect_raw_rows",
                "pdf.detect_tables",
                "pdf.table_from_header",
            }:
                raise ProfileError(
                    "table.map_columns input must refer to a prior table-producing step"
                )
        elif "input" in step:
            raise ProfileError(f"Operation {step['op']} does not support an input alias")
    if sum(x["op"] == "table.map_columns" for x in steps) > 1:
        raise ProfileError("V1 supports only one table.map_columns step per profile")
    if sum(x["op"] in {"pdf.detect_tables", "pdf.table_from_header"} for x in steps) > 1:
        raise ProfileError("Only one PDF table strategy may be selected per profile")
    if sum(x["op"] == "csv.collect_raw_rows" for x in steps) > 1:
        raise ProfileError("Only one CSV reading step may be selected per profile")
    if kind == "source" and not any(x["op"] == "table.map_columns" for x in steps):
        raise ProfileError("Source profiles in V1 must include table.map_columns")
    if "output" in body:
        output = _string_map(body["output"], keys={"kind"}, label="output")
        if output.get("kind") not in {"tables", "records", "document", "document_with_tables"}:
            raise ProfileError("Unsupported output kind")
    if "validation" in body:
        _string_map(
            body["validation"],
            keys={
                "require_provenance",
                "ambiguous_dialect",
                "ambiguous_structure",
                "uncertain_reading_order",
                "missing_required_column",
                "layout_mismatch",
            },
            label="validation",
        )
    return Profile(
        id=pid,
        version=version,
        kind=kind,
        file_format=fmt,
        pipeline=tuple(steps),
        match=match,
        sha256=hashlib.sha256(data).hexdigest(),
        source=source,
    )


def load_file(path: str | Path) -> Profile:
    p = Path(path).expanduser()
    try:
        if not p.is_file():
            raise ProfileError("Profile file does not exist")
        if p.stat().st_size > MAX_YAML_BYTES:
            raise ProfileError("YAML profile exceeds 128 KiB")
        with p.open("rb") as f:
            data = f.read(MAX_YAML_BYTES + 1)
    except OSError as exc:
        raise ProfileError("Unable to read profile file") from exc
    return from_bytes(data, source="local-file")


def builtin_profile_ids() -> list[str]:
    return sorted(p.id for p in _bundled_profiles())


def _bundled_profiles() -> list[Profile]:
    root = resources.files("doc_extractor").joinpath("presets")
    result = []
    for item in root.iterdir():
        if item.name.endswith(".yaml"):
            result.append(from_bytes(item.read_bytes(), source="built-in"))
    return result


def load_builtin(profile_id: str) -> Profile:
    for profile in _bundled_profiles():
        if profile.id == profile_id:
            return profile
    raise ProfileError("Unknown bundled preset ID")


def installed_profile_ids() -> list[str]:
    return sorted(ep.name for ep in metadata.entry_points(group="doc_extractor.profiles"))


def load_installed(profile_id: str) -> Profile:
    """Only explicitly selected, trusted installed plugins are executed."""
    for ep in metadata.entry_points(group="doc_extractor.profiles"):
        if ep.name == profile_id:
            try:
                factory = ep.load()
                profile = factory()
            except Exception as exc:
                raise ProfileError("Installed profile plugin failed to load") from exc
            if not isinstance(profile, Profile) or profile.id != profile_id:
                raise ProfileError("Installed profile plugin returned an invalid profile")
            return profile
    raise ProfileError("Profile ID is not installed; use --profile-file for a custom YAML")
