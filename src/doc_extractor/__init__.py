"""Local-first PDF/CSV extraction, without requiring a finance application."""

from .api import extract, inspect_file
from .models import (
    Cell,
    ExtractionResult,
    Issue,
    Location,
    Page,
    RecordSet,
    Table,
    TextBlock,
    Value,
)
from .utils import Limits

__version__ = "0.1.0"
__all__ = [
    "Cell",
    "ExtractionResult",
    "Issue",
    "Limits",
    "Location",
    "Page",
    "RecordSet",
    "Table",
    "TextBlock",
    "Value",
    "extract",
    "inspect_file",
]
