"""Stable Python API shared by command-line and future consuming applications."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from importlib import metadata
from io import BytesIO
from pathlib import Path
from typing import Any

import pdfplumber

from .errors import ProfileError, UnsupportedFileError
from .models import ExtractionResult, Issue
from .profiles import apply_mapping, load_builtin, load_file, load_installed, match_profile
from .readers.csv_reader import read_csv
from .readers.pdf_reader import read_pdf
from .utils import Limits, read_source

MODES = {"all", "content", "tables", "records"}


def extract(
    path: str | Path,
    *,
    mode: str = "all",
    preset: str | None = None,
    profile: str | None = None,
    profile_file: str | Path | None = None,
    delimiter: str | None = None,
    encoding: str | None = None,
    csv_header: bool | None = None,
    limits: Limits | None = None,
) -> ExtractionResult:
    """Extract text, tables or records from one PDF or CSV file.

    Parameters
    ----------
    path
        PDF or CSV file. Only its basename and SHA-256 are recorded in the result.
    mode
        ``"all"`` (text and tables), ``"content"`` (PDF text only), ``"tables"`` or
        ``"records"`` (fields mapped by a source profile).
    preset
        ID of a built-in generic preset, e.g. ``"preset.pdf.tables.borderless.v1"``.
    profile
        ID of a source profile from a trusted installed package.
    profile_file
        Path to a YAML source profile. ``preset``, ``profile`` and ``profile_file`` are
        mutually exclusive.
    delimiter, encoding, csv_header
        CSV overrides; they take precedence over values in a profile.
    limits
        Resource limits; defaults to :class:`~doc_extractor.Limits`.

    Returns
    -------
    ExtractionResult
        Pages, tables, record sets, issues and provenance. ``result.needs_review`` is
        ``True`` when a warning requires a human look.

    Raises
    ------
    doc_extractor.errors.DocExtractError
        Unsupported or unreadable input, invalid profile, or an exceeded limit.

    Examples
    --------
    >>> result = extract("statement.pdf", mode="records", profile_file="bank.yaml")
    >>> result.record_sets[0].records[0]["amount"].normalized
    '-850.00'
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {sorted(MODES)}")
    if sum(bool(x) for x in (preset, profile, profile_file)) > 1:
        raise ProfileError("Choose at most one of preset, profile, or profile_file")
    limits = limits or Limits()
    source = read_source(path, limits)
    kind = source.file_format
    selected = None
    if preset:
        selected = load_builtin(preset)
        if selected.kind != "preset":
            raise ProfileError("--preset requires a generic preset")
    elif profile:
        selected = load_installed(profile)
        if selected.kind != "source":
            raise ProfileError("--profile requires an installed source profile")
    elif profile_file:
        selected = load_file(profile_file)
    if selected and selected.file_format != kind:
        raise ProfileError("Selected profile does not support this file format")

    if mode == "content" and kind == "csv":
        raise UnsupportedFileError("Content mode is for PDF documents; use all or tables for CSV")
    options: dict[str, Any] = {}
    if selected:
        for step in selected.pipeline:
            params = step.get("params", {})
            if step["op"] == "csv.collect_raw_rows":
                for name in ("encoding", "delimiter"):
                    value = params.get(name)
                    if value and value != "detect_or_require_override":
                        options[name] = value
                if "first_row_header" in params:
                    options["csv_header"] = params["first_row_header"]
            elif step["op"] == "pdf.table_from_header":
                options["header_table"] = params
            elif step["op"] == "pdf.detect_tables":
                options["table_settings"] = {
                    k: v
                    for k, v in params.items()
                    if k not in {"include_cell_bbox", "preserve_raw_cells"}
                }
    if delimiter is not None:
        options["delimiter"] = delimiter
    if encoding is not None:
        options["encoding"] = encoding
    if csv_header is not None:
        options["csv_header"] = csv_header

    backend_version = pdfplumber.__version__ if kind == "pdf" else "stdlib csv"
    result = ExtractionResult(
        source_name=source.basename,
        sha256=source.sha256,
        size_bytes=source.size_bytes,
        file_format=kind,
        mode=mode,
        reader_version=metadata.version("doc-extractor") if _installed() else "0.1.0",
        backend_version=backend_version,
        profile_id=selected.id if selected else None,
        profile_version=selected.version if selected else None,
        profile_sha256=selected.sha256 if selected else None,
        run_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    if kind == "csv":
        tables, issues, settings = read_csv(
            source.data,
            suffix=source.suffix,
            limits=limits,
            delimiter=options.get("delimiter"),
            encoding=options.get("encoding"),
            header=options.get("csv_header", True),
        )
        result.tables, result.issues, result.settings = tables, issues, settings
    else:
        result.pages, result.tables, result.issues, result.settings = read_pdf(
            source.data,
            limits=limits,
            include_tables=(
                mode != "content"
                or bool(
                    selected
                    and any(
                        x["op"] in {"pdf.detect_tables", "pdf.table_from_header"}
                        for x in selected.pipeline
                    )
                )
            ),
            table_settings=options.get("table_settings"),
            header_table=options.get("header_table"),
        )

    result.settings["limits"] = asdict(limits)
    if selected:
        match = match_profile(selected, result)
        result.settings["profile_match_checks"] = [
            {"check": name, "matched": passed} for name, passed in match.checks
        ]
        if not match.matched:
            result.issues.append(
                Issue("LAYOUT_MISMATCH", "Profile fingerprint does not match source structure.")
            )
        elif selected.kind == "source":
            apply_mapping(selected, result)
    if mode == "records" and (selected is None or selected.kind != "source"):
        result.issues.append(
            Issue(
                "PROFILE_REQUIRED",
                "Record extraction requires an explicit matching source profile.",
            )
        )
    if mode == "records" and not result.record_sets:
        result.issues.append(
            Issue("NO_VALIDATED_RECORDS", "No records were mapped; review source and profile.")
        )
    if mode == "content":
        result.tables.clear()
        result.record_sets.clear()
    if mode == "tables":
        result.pages.clear()
        result.record_sets.clear()
    return result


def _installed() -> bool:
    try:
        metadata.version("doc-extractor")
    except metadata.PackageNotFoundError:
        return False
    return True


def inspect_file(path: str | Path, *, limits: Limits | None = None) -> dict[str, Any]:
    """Return file name, format, size, SHA-256 and page count (PDF) or guessed delimiter (CSV).

    Reads no document content into the result and never returns the absolute path.
    """
    limits = limits or Limits()
    source = read_source(path, limits)
    kind = source.file_format
    if kind == "csv":
        # Avoid reading entire CSV or extracting personal data just to inspect it.
        import csv

        head = source.data[:32768]
        try:
            text = head.decode("utf-8-sig")
            dialect = csv.Sniffer().sniff(text, delimiters=",;\t|")
            delim = dialect.delimiter
        except (UnicodeError, csv.Error):
            delim = None
        return {
            "source_name": source.basename,
            "format": kind,
            "size_bytes": source.size_bytes,
            "sha256": source.sha256,
            "possible_delimiter": delim,
        }
    try:
        with pdfplumber.open(BytesIO(source.data)) as pdf:
            pages = len(pdf.pages)
            if pages > limits.max_pages:
                from .errors import InputLimitError

                raise InputLimitError(f"PDF exceeds max_pages ({limits.max_pages})")
            # Text coverage is intentionally not estimated here: no page is rendered.
            return {
                "source_name": source.basename,
                "format": kind,
                "size_bytes": source.size_bytes,
                "sha256": source.sha256,
                "page_count": pages,
            }
    except Exception as exc:
        from .errors import DocExtractError, DocumentReadError

        if isinstance(exc, DocExtractError):
            raise
        raise DocumentReadError("Unable to inspect PDF structure") from exc
