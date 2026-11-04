"""Small typed result contracts independent of a particular DataFrame library."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .errors import ExportError

RESULT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Location:
    """PDF page is one-based; CSV row and column are one-based logical positions."""

    page: int | None = None
    row: int | None = None
    column: int | None = None
    line: int | None = None
    end_line: int | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    severity: str = "warning"  # info | warning | error
    location: Location | None = None


@dataclass(frozen=True)
class TextBlock:
    text: str
    source: Location
    kind: str = "line"


@dataclass
class Page:
    number: int
    text: str
    blocks: list[TextBlock] = field(default_factory=list)


@dataclass(frozen=True)
class Cell:
    text: str | None
    source: Location


@dataclass
class Table:
    id: str
    cells: list[list[Cell]]
    source: Location
    origin: str = "pdf"  # pdf | csv
    header: bool = False

    @property
    def row_count(self) -> int:
        return len(self.cells)

    @property
    def column_count(self) -> int:
        return max((len(row) for row in self.cells), default=0)

    @property
    def rectangular(self) -> bool:
        return all(len(row) == self.column_count for row in self.cells)

    def values(self) -> list[list[str | None]]:
        return [[c.text for c in row] for row in self.cells]

    def _columns_and_rows(
        self, first_row_header: bool | None
    ) -> tuple[list[str], list[list[str | None]]]:
        """Return a loss-aware tabular projection; always retain original cells in JSON."""
        values = self.values()
        if not values or not self.column_count:
            raise ExportError(f"Table {self.id!r} has no cells to export")
        use_header = self.header if first_row_header is None else first_row_header
        if use_header:
            candidates = [str(x or "") for x in values[0]]
            if (
                len(candidates) != self.column_count
                or any(not x.strip() for x in candidates)
                or len(set(candidates)) != len(candidates)
            ):
                raise ExportError(
                    "Header has missing or duplicate names; use first_row_header=False"
                )
            columns = candidates
            rows = values[1:]
        else:
            columns = [f"column_{n}" for n in range(1, self.column_count + 1)]
            rows = values
        # Padding is disclosed by the ``rectangular`` flag in the result manifest.
        return columns, [r + [None] * (self.column_count - len(r)) for r in rows]

    def to_polars(self, *, first_row_header: bool | None = None) -> Any:
        """Convert a table lazily; Polars is optional and not imported by the core reader."""
        try:
            import polars as pl
        except ImportError as exc:
            raise ExportError("Polars is required: pip install 'doc-extractor[tabular]'") from exc
        columns, rows = self._columns_and_rows(first_row_header)
        # Force string schema to avoid turning identifiers/dates/locale amounts into guesses.
        return pl.DataFrame(
            {
                name: pl.Series(name, [row[i] for row in rows], dtype=pl.String)
                for i, name in enumerate(columns)
            }
        )

    def to_arrow(self, *, first_row_header: bool | None = None) -> Any:
        try:
            import pyarrow  # noqa: F401
        except ImportError as exc:
            raise ExportError("PyArrow is required: pip install 'doc-extractor[arrow]'") from exc
        return self.to_polars(first_row_header=first_row_header).to_arrow()

    def to_pandas(self, *, first_row_header: bool | None = None) -> Any:
        try:
            import pandas  # noqa: F401
        except ImportError as exc:
            raise ExportError("Pandas is required: pip install 'doc-extractor[pandas]'") from exc
        try:
            return self.to_polars(first_row_header=first_row_header).to_pandas()
        except ImportError as exc:
            raise ExportError(
                "Pandas conversion also requires PyArrow: pip install 'doc-extractor[pandas]'"
            ) from exc


@dataclass(frozen=True)
class Value:
    raw: str | None
    normalized: str | None
    normalized_type: str | None
    source: Location
    normalization_requested: bool = False


@dataclass
class RecordSet:
    id: str
    records: list[dict[str, Value]]
    source_table_id: str

    def to_polars(self, *, normalized: bool = False, include_normalized: bool = False) -> Any:
        """String-typed frame of the records.

        ``normalized=True`` replaces values with their normalized form where the profile
        requested parsing. ``include_normalized=True`` keeps the raw columns and adds a
        ``<field>_normalized`` column for every field the profile normalizes.
        """
        try:
            import polars as pl
        except ImportError as exc:
            raise ExportError("Polars is required: pip install 'doc-extractor[tabular]'") from exc
        columns = list(self.records[0]) if self.records else []
        data: dict[str, Any] = {
            col: pl.Series(
                col,
                [
                    (row[col].normalized if row[col].normalization_requested else row[col].raw)
                    if normalized
                    else row[col].raw
                    for row in self.records
                ],
                dtype=pl.String,
            )
            for col in columns
        }
        if include_normalized:
            for col in columns:
                if not any(row[col].normalization_requested for row in self.records):
                    continue
                name = f"{col}_normalized"
                if name in data:
                    raise ExportError(f"Field {name!r} collides with a normalized column")
                data[name] = pl.Series(
                    name, [row[col].normalized for row in self.records], dtype=pl.String
                )
        return pl.DataFrame(data)


@dataclass
class ExtractionResult:
    source_name: str
    sha256: str
    size_bytes: int
    file_format: str
    mode: str
    reader_version: str
    backend_version: str
    profile_id: str | None = None
    profile_version: str | None = None
    profile_sha256: str | None = None
    run_at_utc: str = ""
    pages: list[Page] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    record_sets: list[RecordSet] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    result_schema_version: int = RESULT_SCHEMA_VERSION

    @property
    def needs_review(self) -> bool:
        return any(x.severity in ("warning", "error") for x in self.issues)

    def to_dict(self) -> dict[str, Any]:
        obj = asdict(self)
        obj["status"] = "needs_review" if self.needs_review else "ok"
        return obj
