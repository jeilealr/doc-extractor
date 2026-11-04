"""Resource limits and one immutable in-memory source snapshot per extraction."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import DocumentReadError, InputLimitError, UnsupportedFileError


@dataclass(frozen=True)
class Limits:
    max_bytes: int = 64 * 1024 * 1024
    max_pages: int = 150
    max_rows: int = 200_000
    max_tables_per_page: int = 50
    max_chars_per_page: int = 2_000_000

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class SourceBytes:
    """The parser reads precisely the byte sequence whose SHA-256 we record."""

    basename: str
    suffix: str
    file_format: str
    size_bytes: int
    sha256: str
    data: bytes = field(repr=False)


def read_source(path: str | Path, limits: Limits) -> SourceBytes:
    p = Path(path).expanduser()
    try:
        if not p.is_file():
            raise UnsupportedFileError("Input must be an existing regular file")
        if p.stat().st_size > limits.max_bytes:
            raise InputLimitError(f"Input exceeds max_bytes ({limits.max_bytes} bytes)")
        with p.open("rb") as f:
            data = f.read(limits.max_bytes + 1)
    except OSError as exc:
        raise DocumentReadError("Unable to read input file") from exc
    if len(data) > limits.max_bytes:
        raise InputLimitError(f"Input exceeds max_bytes ({limits.max_bytes} bytes)")
    if not data:
        raise UnsupportedFileError("Empty input file")
    if data.startswith(b"%PDF-"):
        kind = "pdf"
    elif p.suffix.lower() in {".csv", ".tsv"}:
        kind = "csv"
    elif p.suffix.lower() == ".pdf":
        raise UnsupportedFileError("File extension is .pdf but the PDF signature is missing")
    else:
        raise UnsupportedFileError("Only PDF, CSV, and TSV inputs are currently supported")
    return SourceBytes(
        basename=p.name,
        suffix=p.suffix.lower(),
        file_format=kind,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        data=data,
    )


def rounded_bbox(raw: object) -> tuple[float, float, float, float] | None:
    if raw is None:
        return None
    try:
        values = tuple(round(float(n), 2) for n in raw)  # type: ignore[union-attr]
    except (TypeError, ValueError):
        return None
    return values if len(values) == 4 else None
