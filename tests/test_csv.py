from __future__ import annotations

import pytest

from doc_extractor import Limits, extract, inspect_file
from doc_extractor.errors import DocumentReadError, InputLimitError


def test_payback_raw_csv_and_references(payback_csv):
    result = extract(payback_csv, mode="all")
    table = result.tables[0]
    assert result.file_format == "csv"
    assert result.sha256 and len(result.sha256) == 64
    assert table.row_count == 3 and table.column_count == 3
    assert table.cells[1][2].text == "1.000,50"
    assert table.cells[1][2].source.row == 2
    assert table.cells[1][2].source.column == 3
    assert table.cells[1][2].source.line == 2
    assert result.settings["encoding"] == "utf-8-sig"
    assert result.source_name == "activity.csv"


def test_csv_semicolon_and_quoted_newline(tmp_path):
    path = tmp_path / "measurements.csv"
    path.write_text('name;value\n"first\nsecond";"1,25"\nother;"1,30"\n', encoding="utf-8")
    result = extract(path)
    assert result.settings["delimiter"] == ";"
    assert result.tables[0].cells[1][0].text == "first\nsecond"
    assert result.tables[0].cells[1][0].source.line == 2
    assert result.tables[0].cells[1][0].source.end_line == 3


def test_csv_non_utf8_explicit_encoding(tmp_path):
    path = tmp_path / "latin.csv"
    path.write_bytes("label,val\nCafé,32\n".encode("cp1252"))
    with pytest.raises(DocumentReadError):
        extract(path)
    result = extract(path, encoding="cp1252")
    assert result.tables[0].cells[1][0].text == "Café"


def test_csv_no_header(tmp_path):
    path = tmp_path / "numbers.csv"
    path.write_text("0004,9\n0005,10\n")
    result = extract(path, csv_header=False)
    assert result.tables[0].header is False
    assert result.tables[0].cells[0][0].text == "0004"


def test_csv_ragged_and_limit(tmp_path):
    path = tmp_path / "ragged.csv"
    path.write_text("A,B\n1\n3,4,5\n")
    result = extract(path)
    assert "CSV_RAGGED_ROWS" in {i.code for i in result.issues}
    with pytest.raises(InputLimitError):
        extract(path, limits=Limits(max_rows=2))


def test_csv_formula_string_preserved_not_executed(tmp_path):
    path = tmp_path / "injection.csv"
    path.write_text("Value,Notes\n=1+2,test\n", encoding="utf-8")
    result = extract(path)
    assert result.tables[0].cells[1][0].text == "=1+2"


def test_csv_invalid_encoding_and_delimiter(payback_csv):
    with pytest.raises(DocumentReadError):
        extract(payback_csv, delimiter="not-a-delimiter")
    with pytest.raises(DocumentReadError):
        extract(payback_csv, encoding="utf-16")


def test_inspect_does_not_expose_data_or_path(payback_csv):
    report = inspect_file(payback_csv)
    assert report["format"] == "csv"
    assert "Book purchase" not in repr(report)
    assert str(payback_csv.parent) not in repr(report)
