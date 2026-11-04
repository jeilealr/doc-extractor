"""Generic PDF text + table extraction using pdfplumber (MIT licensed)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pdfplumber

from ..errors import DocumentReadError, InputLimitError
from ..models import Cell, Issue, Location, Page, Table, TextBlock
from ..utils import Limits, rounded_bbox
from .header_table import table_from_header, validate_header_table_settings

ALLOWED_TABLE_STRATEGIES = {"lines", "lines_strict", "text"}


def validate_table_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    """Reject unexpected knobs rather than allowing YAML to pass arbitrary backend parameters."""
    if settings is None:
        return {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
    allowed = {
        "vertical_strategy",
        "horizontal_strategy",
        "min_words_vertical",
        "min_words_horizontal",
        "snap_tolerance",
        "join_tolerance",
        "intersection_tolerance",
        "text_x_tolerance",
        "text_y_tolerance",
    }
    unknown = set(settings) - allowed
    if unknown:
        raise DocumentReadError("Unsupported PDF table settings: " + ", ".join(sorted(unknown)))
    chosen = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
    chosen.update(settings)
    for axis in ("vertical_strategy", "horizontal_strategy"):
        if not isinstance(chosen[axis], str) or chosen[axis] not in ALLOWED_TABLE_STRATEGIES:
            raise DocumentReadError(f"Unsupported PDF {axis}")
    for key, value in chosen.items():
        if key.startswith("min_words_"):
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 50:
                raise DocumentReadError(f"Invalid PDF table setting {key}")
        elif key.endswith("_tolerance"):
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0 <= value <= 20
            ):
                raise DocumentReadError(f"Invalid PDF table setting {key}")
    return chosen


def read_pdf(
    data: bytes,
    *,
    limits: Limits,
    include_tables: bool = True,
    table_settings: dict[str, Any] | None = None,
    header_table: dict[str, Any] | None = None,
) -> tuple[list[Page], list[Table], list[Issue], dict[str, Any]]:
    settings = validate_table_settings(table_settings)
    header_settings = validate_header_table_settings(header_table) if header_table else None
    pages: list[Page] = []
    tables: list[Table] = []
    issues: list[Issue] = []
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            if len(pdf.pages) > limits.max_pages:
                raise InputLimitError(f"PDF exceeds max_pages ({limits.max_pages})")
            for page_number, pdf_page in enumerate(pdf.pages, start=1):
                if len(pdf_page.chars) > limits.max_chars_per_page:
                    raise InputLimitError(f"PDF page {page_number} exceeds max_chars_per_page")
                source_lines = pdf_page.extract_text_lines(strip=False, return_chars=False)
                blocks = []
                for source_line in source_lines:
                    bbox = rounded_bbox(
                        (
                            source_line.get("x0"),
                            source_line.get("top"),
                            source_line.get("x1"),
                            source_line.get("bottom"),
                        )
                    )
                    blocks.append(
                        TextBlock(
                            text=str(source_line.get("text", "")),
                            source=Location(page=page_number, bbox=bbox),
                        )
                    )
                # This is a heuristic text-layer reading order, not a semantic reconstruction.
                content = "\n".join(line.text for line in blocks)
                pages.append(Page(number=page_number, text=content, blocks=blocks))
                if not blocks:
                    issues.append(
                        Issue(
                            "OCR_REQUIRED",
                            "This PDF page has no extractable text layer.",
                            location=Location(page=page_number),
                        )
                    )
                if not include_tables:
                    pdf_page.flush_cache()
                    continue
                if header_settings is not None:
                    table, table_issues = table_from_header(
                        pdf_page.extract_words(), page_number, header_settings
                    )
                    tables.extend([table] if table else [])
                    issues.extend(table_issues)
                    pdf_page.flush_cache()
                    continue
                found = pdf_page.find_tables(table_settings=settings)
                if len(found) > limits.max_tables_per_page:
                    raise InputLimitError(f"PDF page {page_number} exceeds max_tables_per_page")
                for index, found_table in enumerate(found, start=1):
                    raw_rows = found_table.extract()
                    cells: list[list[Cell]] = []
                    for row_idx, row in enumerate(raw_rows, start=1):
                        geometries = found_table.rows[row_idx - 1].cells
                        cells.append(
                            [
                                Cell(
                                    text=raw_text,
                                    source=Location(
                                        page=page_number,
                                        row=row_idx,
                                        column=col_idx,
                                        bbox=rounded_bbox(
                                            geometries[col_idx - 1]
                                            if col_idx - 1 < len(geometries)
                                            else None
                                        ),
                                    ),
                                )
                                for col_idx, raw_text in enumerate(row, start=1)
                            ]
                        )
                    tables.append(
                        Table(
                            id=f"pdf_p{page_number}_t{index}",
                            cells=cells,
                            source=Location(page=page_number, bbox=rounded_bbox(found_table.bbox)),
                        )
                    )
                # A PDF can contain many pages and pdfplumber caches large word/object lists.
                # The result already contains detached plain Python values.
                pdf_page.flush_cache()
    except InputLimitError:
        raise
    except (ValueError, TypeError, OSError, KeyError, IndexError) as exc:
        raise DocumentReadError("Unable to parse PDF content or tables") from exc
    except Exception as exc:
        # PDF parsers can throw backend-specific exceptions for damaged/encrypted documents.
        raise DocumentReadError(f"PDF processing failed ({type(exc).__name__})") from exc
    if pages:
        issues.append(
            Issue(
                "PDF_READING_ORDER_HEURISTIC",
                "PDF text-layer line order has not been visually verified; multi-column pages may need review.",
                severity="info",
            )
        )
    if include_tables and tables:
        issues.append(
            Issue(
                "PDF_TABLE_STRUCTURE_HEURISTIC",
                "Detected PDF tables are candidates; inspect source regions for complex layouts.",
                severity="info",
            )
        )
    if include_tables and not tables:
        issues.append(
            Issue(
                "NO_TABLES_FOUND",
                "No ruled tables detected. Try --preset preset.pdf.tables.borderless.v1 for tables "
                "without cell borders, a profile with pdf.table_from_header if you know the "
                "column names, or --mode content for the page text.",
                severity="info",
            )
        )
    effective = {"header_table": header_settings} if header_settings else settings
    return pages, tables, issues, {"table_settings": effective, "page_count": len(pages)}
