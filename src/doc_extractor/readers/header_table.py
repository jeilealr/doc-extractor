"""Tables located by their header row: for layouts without usable cell borders.

Many statements and invoices draw no (or only image) lines, so line-based table detection
finds nothing and text-alignment detection cuts words in half. If a profile knows the
column names, the header row itself gives everything needed:

1. the header line is found by its column names, in order (a name may span several words);
2. column boundaries lie halfway between neighbouring header names, unless the profile
   gives explicit ``columns_x``;
3. words below the header, up to an end marker, are grouped into lines by their vertical
   position and each word goes to the column containing its horizontal centre;
4. with ``new_row_column``, a line whose cell in that column is empty continues the
   previous row (multi-line descriptions).

Nothing is guessed silently: words straddling a column boundary and continuation lines
without a preceding row are reported as issues.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence
from itertools import pairwise
from typing import Any

from ..errors import ProfileError
from ..models import Cell, Issue, Location, Table
from ..utils import rounded_bbox

PARAMS = {"header", "end_before_text", "new_row_column", "columns_x", "y_tolerance"}
DEFAULT_Y_TOLERANCE = 3.0


def validate_header_table_settings(params: dict[str, Any]) -> dict[str, Any]:
    """Check profile parameters; return them with defaults filled in."""
    unknown = set(params) - PARAMS
    if unknown:
        raise ProfileError(
            "Unsupported pdf.table_from_header parameter(s): " + ", ".join(sorted(unknown))
        )
    header = params.get("header")
    if (
        not isinstance(header, list)
        or not 2 <= len(header) <= 40
        or not all(isinstance(h, str) and h.strip() and len(h) <= 100 for h in header)
        or len({h.strip().casefold() for h in header}) != len(header)
    ):
        raise ProfileError("header must list 2 to 40 distinct, non-empty column names")
    end = params.get("end_before_text", [])
    if (
        not isinstance(end, list)
        or len(end) > 20
        or not all(isinstance(t, str) and t.strip() and len(t) <= 200 for t in end)
    ):
        raise ProfileError("end_before_text must be a list of up to 20 non-empty strings")
    new_row = params.get("new_row_column")
    if new_row is not None and new_row not in header:
        raise ProfileError("new_row_column must be one of the header names")
    columns_x = params.get("columns_x")
    if columns_x is not None and (
        not isinstance(columns_x, list)
        or len(columns_x) != len(header) - 1
        or not all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x <= 10_000
            for x in columns_x
        )
        or any(b <= a for a, b in pairwise(columns_x))
    ):
        raise ProfileError(
            "columns_x must list len(header) - 1 strictly increasing positions (PDF points)"
        )
    tolerance = params.get("y_tolerance", DEFAULT_Y_TOLERANCE)
    if (
        not isinstance(tolerance, (int, float))
        or isinstance(tolerance, bool)
        or not (0 <= tolerance <= 20)
    ):
        raise ProfileError("y_tolerance must be a number between 0 and 20")
    return {
        "header": [h.strip() for h in header],
        "end_before_text": end,
        "new_row_column": new_row,
        "columns_x": columns_x,
        "y_tolerance": float(tolerance),
    }


def _lines(words: Sequence[dict[str, Any]], tolerance: float) -> list[list[dict[str, Any]]]:
    """Group words whose top edges are within ``tolerance`` points; sort each line by x."""
    lines: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and word["top"] - lines[-1][0]["top"] <= tolerance:
            lines[-1].append(word)
        else:
            lines.append([word])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def _find_header(
    line: list[dict[str, Any]], header: list[str]
) -> list[list[dict[str, Any]]] | None:
    """Return the words of each header name if the line contains all names, in order."""
    found: list[list[dict[str, Any]]] = []
    start = 0
    for name in header:
        parts = [p.casefold() for p in name.split()]
        for k in range(start, len(line) - len(parts) + 1):
            if [w["text"].casefold() for w in line[k : k + len(parts)]] == parts:
                found.append(line[k : k + len(parts)])
                start = k + len(parts)
                break
        else:
            return None
    return found


def _union(boxes: Sequence[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def _box(word: dict[str, Any]) -> tuple[float, float, float, float]:
    return (word["x0"], word["top"], word["x1"], word["bottom"])


def _best_boundary(lo: float, hi: float, words: Sequence[dict[str, Any]]) -> float:
    """Pick the x between two header names that cuts the fewest body words.

    Left-aligned text extends right towards the next column and right-aligned numbers
    extend left under their header, so the plain midpoint often cuts words. The empty
    vertical gap between the columns is the natural boundary. With few rows, the spaces
    between words can be just as empty, so among equally clean gaps the widest wins (a
    column gap is wider than a word space); remaining ties prefer the midpoint.
    """
    middle = (lo + hi) / 2
    if hi <= lo:
        return middle
    points = sorted({lo, hi, *(x for w in words for x in (w["x0"], w["x1"]) if lo < x < hi)})

    def rank(gap: tuple[float, float]) -> tuple[int, float, float]:
        x = (gap[0] + gap[1]) / 2
        return sum(w["x0"] < x < w["x1"] for w in words), gap[0] - gap[1], abs(x - middle)

    a, b = min(pairwise(points), key=rank)
    return (a + b) / 2


def table_from_header(
    words: Sequence[dict[str, Any]], page_number: int, settings: dict[str, Any]
) -> tuple[Table | None, list[Issue]]:
    """Build one table from a page's words, or ``None`` if the header is not on this page."""
    header: list[str] = settings["header"]
    lines = _lines(words, settings["y_tolerance"])
    issues: list[Issue] = []
    found = next(
        ((i, ws) for i, line in enumerate(lines) if (ws := _find_header(line, header))), None
    )
    if found is None:
        return None, issues
    index, header_words = found

    spans = [_union([_box(w) for w in ws]) for ws in header_words]
    body: list[list[dict[str, Any]]] = []
    for line in lines[index + 1 :]:
        text = " ".join(w["text"] for w in line)
        if any(marker in text for marker in settings["end_before_text"]):
            break
        body.append(line)
    body_words = [w for line in body for w in line]
    boundaries: list[float] = settings["columns_x"] or [
        _best_boundary(left[2], right[0], body_words) for left, right in pairwise(spans)
    ]

    left = min([spans[0][0]] + [w["x0"] for line in body for w in line])
    right = max([spans[-1][2]] + [w["x1"] for line in body for w in line])
    edges = [left, *boundaries, right]
    new_row = header.index(settings["new_row_column"]) if settings["new_row_column"] else None

    # rows -> columns -> lines -> words; a cell keeps one entry per source line.
    rows: list[list[list[list[dict[str, Any]]]]] = []
    for line in body:
        columns: list[list[dict[str, Any]]] = [[] for _ in header]
        for word in line:
            centre = (word["x0"] + word["x1"]) / 2
            columns[bisect_right(boundaries, centre)].append(word)
            if any(word["x0"] < b < word["x1"] for b in boundaries):
                issues.append(
                    Issue(
                        "TABLE_WORD_CROSSES_COLUMN",
                        "A word straddles a column boundary; check columns_x for this layout.",
                        location=Location(page=page_number, bbox=rounded_bbox(_box(word))),
                    )
                )
        if new_row is not None and not columns[new_row]:
            if not rows:
                issues.append(
                    Issue(
                        "TABLE_ROW_WITHOUT_START",
                        "A table line appears before the first row start and was skipped.",
                        location=Location(
                            page=page_number, bbox=rounded_bbox(_union([_box(w) for w in line]))
                        ),
                    )
                )
                continue
            for target, extra in zip(rows[-1], columns, strict=True):
                if extra:
                    target.append(extra)
            continue
        rows.append([[ws] if ws else [] for ws in columns])

    def cell(
        lines_: list[list[dict[str, Any]]], row: int, col: int, top: float, bottom: float
    ) -> Cell:
        flat = [w for ws in lines_ for w in ws]
        text = "\n".join(" ".join(w["text"] for w in ws) for ws in lines_)
        box = _union([_box(w) for w in flat]) if flat else (edges[col - 1], top, edges[col], bottom)
        return Cell(
            text=text,
            source=Location(page=page_number, row=row, column=col, bbox=rounded_bbox(box)),
        )

    cells = [
        [
            cell([ws], 1, c, spans[c - 1][1], spans[c - 1][3])
            for c, ws in enumerate(header_words, start=1)
        ]
    ]
    for r, columns in enumerate(rows, start=2):
        boxes = [_box(w) for col in columns for ws in col for w in ws]
        top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
        cells.append([cell(col, r, c, top, bottom) for c, col in enumerate(columns, start=1)])
    table_box = _union([spans[0], spans[-1]] + [c.source.bbox for row in cells for c in row])
    table = Table(
        id=f"pdf_p{page_number}_t1",
        cells=cells,
        source=Location(page=page_number, bbox=rounded_bbox(table_box)),
        header=True,
    )
    return table, issues
