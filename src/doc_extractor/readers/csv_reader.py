"""Loss-aware CSV/TSV reading: retain observed field strings and source line numbers."""

from __future__ import annotations

import csv
import io

from ..errors import DocumentReadError, InputLimitError
from ..models import Cell, Issue, Location, Table
from ..utils import Limits

_DELIMITERS = {",", ";", "\t", "|"}


def read_csv(
    data: bytes,
    *,
    suffix: str,
    limits: Limits,
    encoding: str | None = None,
    delimiter: str | None = None,
    header: bool = True,
) -> tuple[list[Table], list[Issue], dict[str, str | bool]]:
    if delimiter is not None and delimiter not in _DELIMITERS:
        raise DocumentReadError("CSV delimiter must be a comma, semicolon, tab, or pipe")
    if encoding is not None and encoding.lower().replace("_", "-") not in {
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "iso-8859-1",
        "latin-1",
    }:
        raise DocumentReadError("Unsupported CSV encoding override")
    try:
        chosen_encoding = encoding or "utf-8-sig"
        text = data.decode(chosen_encoding, errors="strict")
    except UnicodeError as exc:
        raise DocumentReadError(
            "CSV cannot be decoded as UTF-8. Select --encoding cp1252 or latin-1 explicitly."
        ) from exc

    issues: list[Issue] = []
    if delimiter is None:
        try:
            inferred = csv.Sniffer().sniff(text[:32768], delimiters=",;\t|")
            delimiter = inferred.delimiter
        except csv.Error:
            delimiter = "\t" if suffix == ".tsv" else ","
            issues.append(
                Issue(
                    "CSV_DIALECT_UNCERTAIN",
                    "Unable to confidently determine a delimiter; using a default. Override with --delimiter.",
                )
            )
    if delimiter not in _DELIMITERS:
        raise DocumentReadError("Detected unsupported CSV delimiter")

    rows: list[list[Cell]] = []
    line_end = 0
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        for logical_row, fields in enumerate(reader, start=1):
            if logical_row > limits.max_rows:
                raise InputLimitError(f"CSV exceeds max_rows ({limits.max_rows})")
            line_start = line_end + 1
            line_end = reader.line_num
            rows.append(
                [
                    Cell(
                        value,
                        Location(row=logical_row, column=col, line=line_start, end_line=line_end),
                    )
                    for col, value in enumerate(fields, start=1)
                ]
            )
    except (csv.Error, OverflowError) as exc:
        raise DocumentReadError(f"Malformed CSV at or near physical line {line_end + 1}") from exc
    if not rows:
        issues.append(Issue("CSV_EMPTY", "No CSV records were found."))
    elif len({len(row) for row in rows}) > 1:
        issues.append(
            Issue(
                "CSV_RAGGED_ROWS",
                "CSV rows have different field counts; original rows are preserved.",
            )
        )
    if header and rows:
        names = [c.text or "" for c in rows[0]]
        if len(names) != len(set(names)) or any(not n.strip() for n in names):
            issues.append(
                Issue(
                    "CSV_HEADER_UNCERTAIN",
                    "Header row has blank or duplicated names; tabular header export may require an override.",
                )
            )
    table = Table(id="csv_1", cells=rows, source=Location(row=1), origin="csv", header=header)
    return (
        [table],
        issues,
        {"delimiter": delimiter, "encoding": chosen_encoding, "first_row_header": header},
    )
