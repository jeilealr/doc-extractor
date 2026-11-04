from __future__ import annotations

import pytest

from doc_extractor import Limits, extract, inspect_file
from doc_extractor.errors import DocumentReadError, InputLimitError, UnsupportedFileError


def test_pdf_content_preserves_source_typos(sample_pdf):
    result = extract(sample_pdf, mode="content")
    assert len(result.pages) == 2
    assert not result.tables
    assert "Tpyographic Errror" in result.pages[0].text
    assert "1.000,00" in result.pages[0].text
    assert any("The result was" in b.text for b in result.pages[0].blocks)
    assert result.pages[0].blocks[0].source.bbox is not None
    assert result.pages[0].blocks[0].source.page == 1
    assert result.sha256


def test_pdf_ruled_table_cells_and_bbox(ruled_pdf):
    result = extract(ruled_pdf, mode="all", preset="preset.pdf.tables.ruled.v1")
    assert len(result.tables) >= 1
    table = result.tables[0]
    assert [c.text for c in table.cells[0]] == ["Date", "Description", "Amount"]
    assert table.cells[1][2].text == "1000.00"
    assert table.cells[1][2].source.bbox is not None
    assert table.source.page == 1
    assert table.origin == "pdf"
    assert result.profile_id == "preset.pdf.tables.ruled.v1"


def test_pdf_borderless_preset(borderless_pdf):
    result = extract(borderless_pdf, mode="all", preset="preset.pdf.tables.borderless.v1")
    assert result.settings["table_settings"]["vertical_strategy"] == "text"
    assert result.pages and len(result.pages[0].blocks) >= 4
    assert any(t.column_count >= 2 for t in result.tables)


def test_pdf_max_pages(sample_pdf):
    with pytest.raises(InputLimitError):
        extract(sample_pdf, limits=Limits(max_pages=1))
    with pytest.raises(InputLimitError):
        inspect_file(sample_pdf, limits=Limits(max_pages=1))


def test_pdf_invalid_signature(tmp_path):
    path = tmp_path / "invalid.pdf"
    path.write_text("this is not a pdf")
    with pytest.raises(UnsupportedFileError):
        extract(path)


def test_pdf_corrupt_header(tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-1.7\nnot actually a complete PDF")
    with pytest.raises(DocumentReadError):
        extract(path)


def test_pdf_content_mode_does_not_detect_tables(ruled_pdf):
    result = extract(ruled_pdf, mode="content")
    assert result.pages and not result.tables


def test_pdf_empty_scanned_page_has_ocr_warning(tmp_path):
    from reportlab.pdfgen import canvas

    p = tmp_path / "picture.pdf"
    c = canvas.Canvas(str(p))
    c.rect(50, 50, 100, 100)
    c.showPage()
    c.save()
    result = extract(p, mode="content")
    assert "OCR_REQUIRED" in {i.code for i in result.issues}
