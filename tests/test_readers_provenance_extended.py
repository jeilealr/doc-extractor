"""Uncommon file, parser, and resource-limit error paths."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from reportlab.pdfgen import canvas

from doc_extractor import Limits, extract
from doc_extractor.errors import DocumentReadError, InputLimitError, UnsupportedFileError
from doc_extractor.readers import csv_reader, pdf_reader
from doc_extractor.utils import read_source, rounded_bbox


def test_input_limit_types_are_validated():
    for kwargs in (
        {"max_rows": 0},
        {"max_pages": True},
        {"max_bytes": 1.0},
        {"max_tables_per_page": -1},
        {"max_chars_per_page": "ten"},
    ):
        with pytest.raises(ValueError, match="positive integer"):
            Limits(**kwargs)


def test_empty_source_not_accepted(tmp_path):
    p = tmp_path / "zero.csv"
    p.write_bytes(b"")
    with pytest.raises(UnsupportedFileError, match="Empty input"):
        read_source(p, Limits())


def test_source_permission_is_wrapped_and_does_not_leak_path(tmp_path, monkeypatch):
    p = tmp_path / "private.csv"
    p.write_text("A,B\n1,2\n")
    real_open = Path.open

    def refuse(self, *args, **kwargs):
        if self == p:
            raise PermissionError("PRIVATE SECRET FILE NAME")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse)
    with pytest.raises(DocumentReadError, match="Unable to read") as exc:
        read_source(p, Limits())
    assert "PRIVATE" not in str(exc.value)


def test_snapshot_limit_after_metadata_race(tmp_path, monkeypatch):
    p = tmp_path / "race.csv"
    p.write_bytes(b"X" * 100)
    real_stat = Path.stat

    def pretend_small(self, *args, **kwargs):
        result = real_stat(self, *args, **kwargs)
        if self == p:
            return SimpleNamespace(st_size=1, st_mode=result.st_mode)
        return result

    monkeypatch.setattr(Path, "stat", pretend_small)
    with pytest.raises(InputLimitError, match="max_bytes"):
        read_source(p, Limits(max_bytes=10))


def test_bounding_boxes_have_strict_lengths_and_numbers():
    assert rounded_bbox(None) is None
    assert rounded_bbox([1, 2, 3]) is None
    assert rounded_bbox([0, "not-a-number", 1, 2]) is None
    assert rounded_bbox(17) is None
    assert rounded_bbox((1.234, 2.345, 3.456, 4.567)) == (1.23, 2.35, 3.46, 4.57)


def test_csv_missing_header_duplicate_and_blank(tmp_path):
    p = tmp_path / "header.csv"
    p.write_text("A,A\n1,2\n")
    assert "CSV_HEADER_UNCERTAIN" in {i.code for i in extract(p).issues}
    p.write_text("A,\n1,2\n")
    assert "CSV_HEADER_UNCERTAIN" in {i.code for i in extract(p).issues}
    p.write_text("\n")
    assert "CSV_EMPTY" not in {i.code for i in extract(p).issues}  # physical blank record
    p.write_text("")
    # Empty file is rejected at the source boundary before CSV parsing.
    with pytest.raises(UnsupportedFileError):
        extract(p)
    tables, issues, _ = csv_reader.read_csv(b"", suffix=".csv", limits=Limits())
    assert "CSV_EMPTY" in {i.code for i in issues}
    assert tables[0].cells == []


def test_csv_uncertain_dialect_tsv_and_general_fallback():
    _, issues, settings = csv_reader.read_csv(b"single\n", suffix=".tsv", limits=Limits())
    assert settings["delimiter"] == "\t"
    assert "CSV_DIALECT_UNCERTAIN" in {i.code for i in issues}
    _, issues, settings = csv_reader.read_csv(b"single\n", suffix=".csv", limits=Limits())
    assert settings["delimiter"] == ","
    assert issues


def test_csv_reader_malformed_and_incorrect_sniffer(tmp_path, monkeypatch):
    with pytest.raises(DocumentReadError, match="Malformed CSV"):
        csv_reader.read_csv(
            b'A,B\n"unterminated,1\n', suffix=".csv", limits=Limits(), delimiter=","
        )
    monkeypatch.setattr(
        csv_reader.csv.Sniffer,
        "sniff",
        lambda self, *args, **kwargs: SimpleNamespace(delimiter="?"),
    )
    with pytest.raises(DocumentReadError, match="Detected unsupported"):
        csv_reader.read_csv(b"A,B\n1,2\n", suffix=".csv", limits=Limits())


def test_pdf_settings_reject_unknown_and_valid_tolerance_limits():
    with pytest.raises(DocumentReadError, match="Unsupported PDF table settings"):
        pdf_reader.validate_table_settings({"external_command": "bash"})
    with pytest.raises(DocumentReadError, match="Invalid PDF"):
        pdf_reader.validate_table_settings({"min_words_horizontal": True})
    assert (
        pdf_reader.validate_table_settings(
            {"vertical_strategy": "lines_strict", "snap_tolerance": 5}
        )["snap_tolerance"]
        == 5
    )


def test_pdf_limits_characters_and_number_of_tables(sample_pdf, tmp_path):
    with pytest.raises(InputLimitError, match="max_chars_per_page"):
        extract(sample_pdf, limits=Limits(max_chars_per_page=1))
    p = tmp_path / "two_tables.pdf"
    c = canvas.Canvas(str(p))
    for origin_y in (680, 440):
        for y in (origin_y, origin_y - 30, origin_y - 60):
            c.line(40, y, 250, y)
        for x in (40, 140, 250):
            c.line(x, origin_y, x, origin_y - 60)
    c.save()
    # Explicit document with two separate drawn grids is independently detected.
    normal = extract(p)
    assert len(normal.tables) >= 2
    with pytest.raises(InputLimitError, match="max_tables_per_page"):
        extract(p, limits=Limits(max_tables_per_page=1))


def test_pdf_wraps_backend_errors_without_private_data(monkeypatch):
    def raise_value_error(*args, **kwargs):
        raise ValueError("private content")

    monkeypatch.setattr(pdf_reader.pdfplumber, "open", raise_value_error)
    with pytest.raises(DocumentReadError, match="Unable to parse") as exc:
        pdf_reader.read_pdf(b"%PDF-1.4", limits=Limits())
    assert "private content" not in str(exc.value)

    def raise_unexpected(*args, **kwargs):
        raise RuntimeError("private content")

    monkeypatch.setattr(pdf_reader.pdfplumber, "open", raise_unexpected)
    with pytest.raises(DocumentReadError, match="PDF processing failed \\(RuntimeError\\)") as exc:
        pdf_reader.read_pdf(b"%PDF-1.4", limits=Limits())
    assert "private content" not in str(exc.value)


def test_empty_pdf_page_list_does_not_report_fake_data(monkeypatch):
    class EmptyDoc:
        pages = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(pdf_reader.pdfplumber, "open", lambda *args, **kwargs: EmptyDoc())
    pages, tables, issues, settings = pdf_reader.read_pdf(
        b"%PDF-1.4", limits=Limits(), include_tables=False
    )
    assert not pages and not tables and not issues
    assert settings["page_count"] == 0
