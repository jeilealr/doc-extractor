"""pdf.table_from_header: tables located by their header row, for layouts without cell lines."""

from __future__ import annotations

import textwrap

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from doc_extractor import extract
from doc_extractor.errors import ProfileError
from doc_extractor.profiles import load_file
from doc_extractor.readers.header_table import (
    _best_boundary,
    table_from_header,
    validate_header_table_settings,
)

HEADER = ["Date", "Description", "Amount"]


def word(text, x0, top, width=None):
    width = width if width is not None else 5.0 * len(text)
    return {"text": text, "x0": x0, "x1": x0 + width, "top": top, "bottom": top + 9}


def settings(**overrides):
    return validate_header_table_settings({"header": HEADER, **overrides})


def statement_words():
    """Header at y=100, two rows, one continuation line, an end marker and a footer."""
    return [
        word("Date", 50, 100),
        word("Description", 120, 100),
        word("Amount", 300, 100),
        word("01/02", 50, 115),
        word("Rent", 120, 115),
        word("-850.00", 290, 115),
        word("standing", 120, 127),
        word("order", 165, 127),
        word("02/02", 50, 140),
        word("Salary", 120, 140),
        word("3,250.00", 285, 140),
        word("Total", 120, 160),
        word("Page 1", 50, 800),
    ]


def test_header_rows_columns_and_continuation_lines():
    table, issues = table_from_header(
        statement_words(), 1, settings(end_before_text=["Total"], new_row_column="Date")
    )
    assert issues == []
    assert table.header is True and table.id == "pdf_p1_t1"
    assert table.values() == [
        ["Date", "Description", "Amount"],
        ["01/02", "Rent\nstanding order", "-850.00"],
        ["02/02", "Salary", "3,250.00"],
    ]
    rent = table.cells[1][1].source
    assert (rent.page, rent.row, rent.column) == (1, 2, 2)
    assert rent.bbox == (120, 115, 190, 136)  # union of both description lines


def test_without_new_row_column_every_line_is_a_row_and_empty_cells_get_column_boxes():
    table, _ = table_from_header(statement_words(), 1, settings(end_before_text=["Total"]))
    assert table.values()[2] == ["", "standing order", ""]
    empty = table.cells[2][0].source.bbox
    assert empty[1:] == (127, empty[2], 136)  # spans the row's height in the first column


def test_page_without_header_gives_no_table():
    table, issues = table_from_header([word("Other", 50, 100)], 2, settings())
    assert table is None and issues == []


def test_header_names_may_span_several_words_and_must_be_in_order():
    words = [word("Unit", 50, 10), word("Unit", 100, 10), word("price", 125, 10)]
    table, _ = table_from_header(
        words, 1, validate_header_table_settings({"header": ["Unit", "Unit price"]})
    )
    assert table.values() == [["Unit", "Unit price"]]
    reversed_order = validate_header_table_settings({"header": ["Unit price", "Qty"]})
    assert table_from_header(words + [word("Qty", 10, 10)], 1, reversed_order)[0] is None


def test_continuation_before_first_row_is_reported_and_skipped():
    words = [word("Date", 50, 100), word("Description", 120, 100), word("Amount", 300, 100)]
    words.append(word("orphan", 120, 115))
    table, issues = table_from_header(words, 3, settings(new_row_column="Date"))
    assert table.values() == [HEADER]
    assert [i.code for i in issues] == ["TABLE_ROW_WITHOUT_START"]
    assert issues[0].location.page == 3


def test_explicit_columns_and_words_crossing_them_are_reported():
    words = [word("Date", 50, 100), word("Description", 120, 100), word("Amount", 300, 100)]
    words.append(word("01/02", 50, 115))
    words.append(word("overlong-description", 120, 115, width=200))  # crosses x=280
    table, issues = table_from_header(words, 1, settings(columns_x=[100, 280]))
    assert table.values()[1] == ["01/02", "overlong-description", ""]
    assert [i.code for i in issues] == ["TABLE_WORD_CROSSES_COLUMN"]


def test_single_row_word_spaces_do_not_beat_the_real_column_gap():
    # One transaction only: the space between two description words (5 pt) is as empty as
    # the gap between date and description (16 pt). The wider gap is the column boundary.
    words = [
        word("FECHA", 32, 100, width=30),
        word("DESCRIPCIÓN", 132, 100, width=63),
        word("31/03", 35, 115, width=24),
        word("ABONO", 79, 115, width=24),
        word("INTERESES", 108, 115, width=43),
    ]
    header = validate_header_table_settings({"header": ["FECHA", "DESCRIPCIÓN"]})
    table, _ = table_from_header(words, 1, header)
    assert table.values()[1] == ["31/03", "ABONO INTERESES"]


def test_best_boundary_prefers_the_empty_gap_then_the_midpoint():
    body = [word("workshop", 200, 0, width=50), word("24", 330, 0, width=10)]
    boundary = _best_boundary(150, 325, body)
    assert 250 < boundary < 330  # in the gap, not at the midpoint 237.5 inside "workshop"
    assert _best_boundary(100, 200, []) == 150
    assert _best_boundary(200, 100, []) == 150  # overlapping header names: midpoint


@pytest.mark.parametrize(
    "params,message",
    [
        ({"header": HEADER, "bogus": 1}, "Unsupported"),
        ({"header": "Date"}, "header must"),
        ({"header": ["Date"]}, "header must"),
        ({"header": ["Date", "date"]}, "header must"),
        ({"header": ["Date", " "]}, "header must"),
        ({"header": HEADER, "end_before_text": "Total"}, "end_before_text"),
        ({"header": HEADER, "end_before_text": [""]}, "end_before_text"),
        ({"header": HEADER, "new_row_column": "Balance"}, "new_row_column"),
        ({"header": HEADER, "columns_x": [100]}, "columns_x"),
        ({"header": HEADER, "columns_x": [200, 100]}, "columns_x"),
        ({"header": HEADER, "columns_x": [True, 100]}, "columns_x"),
        ({"header": HEADER, "columns_x": "100,200"}, "columns_x"),
        ({"header": HEADER, "y_tolerance": 50}, "y_tolerance"),
        ({"header": HEADER, "y_tolerance": True}, "y_tolerance"),
    ],
)
def test_invalid_settings_are_rejected(params, message):
    with pytest.raises(ProfileError, match=message):
        validate_header_table_settings(params)


def test_valid_settings_get_defaults():
    assert validate_header_table_settings({"header": [" Date ", "Amount"]}) == {
        "header": ["Date", "Amount"],
        "end_before_text": [],
        "new_row_column": None,
        "columns_x": None,
        "y_tolerance": 3.0,
    }


PROFILE = textwrap.dedent(
    """
    profile_schema_version: 1
    id: test.header_table.v1
    kind: source
    format: pdf
    match:
      required_text: [Example Bank]
      required_headers: [Date, Description, Amount]
    pipeline:
      - op: pdf.table_from_header
        as: tables
        params:
          header: [Date, Description, Amount]
          end_before_text: [Closing balance]
          new_row_column: Date
      - op: table.map_columns
        input: tables
        as: records
        params:
          column_mapping: {Date: date, Description: description, Amount: amount}
          optional_parsing:
            amount: {type: decimal, decimal_separator: '.', thousands_separator: ','}
    """
)


@pytest.fixture
def borderless_statement(tmp_path):
    """Two pages without any drawn lines; the second page has no table header."""
    path = tmp_path / "borderless.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 800, "Example Bank")
    for x, text in ((50, "Date"), (120, "Description"), (330, "Amount")):
        pdf.drawString(x, 760, text)
    rows = [
        ("01/02", "Rent", "-850.00"),
        ("", "standing order", ""),
        ("02/02", "Salary", "3,250.00"),
    ]
    for i, (date, desc, amount) in enumerate(rows):
        y = 744 - 14 * i
        pdf.drawString(50, y, date)
        pdf.drawString(120, y, desc)
        pdf.drawRightString(370, y, amount)
    pdf.drawString(50, 690, "Closing balance 2,400.00")
    pdf.showPage()
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 800, "Thank you for banking with us.")
    pdf.save()
    return path


def test_profile_end_to_end_records(tmp_path, borderless_statement):
    profile = tmp_path / "profile.yaml"
    profile.write_text(PROFILE, encoding="utf-8")
    assert load_file(profile).pipeline[0]["op"] == "pdf.table_from_header"
    result = extract(borderless_statement, mode="records", profile_file=profile)
    assert [t.source.page for t in result.tables] == [1]
    records = result.record_sets[0].records
    assert [r["description"].raw for r in records] == ["Rent\nstanding order", "Salary"]
    assert [r["amount"].normalized for r in records] == ["-850.00", "3250.00"]
    assert result.settings["table_settings"]["header_table"]["new_row_column"] == "Date"
    assert not result.needs_review


def test_profile_rejects_two_table_strategies(tmp_path):
    second = (
        "  - op: pdf.detect_tables\n    as: ruled\n"
        "    params: {vertical_strategy: lines, horizontal_strategy: lines}\n"
    )
    text = PROFILE.replace("  - op: table.map_columns", second + "  - op: table.map_columns")
    profile = tmp_path / "two.yaml"
    profile.write_text(text, encoding="utf-8")
    with pytest.raises(ProfileError, match="Only one PDF table strategy"):
        load_file(profile)


def test_profile_rejects_invalid_header_table_params(tmp_path):
    profile = tmp_path / "bad.yaml"
    profile.write_text(PROFILE.replace("new_row_column: Date", "new_row_column: Balance"))
    with pytest.raises(ProfileError, match="new_row_column"):
        load_file(profile)
