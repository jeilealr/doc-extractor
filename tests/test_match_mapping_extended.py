"""Profile fingerprints, normalization and incomplete row semantics."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from doc_extractor.models import Cell, ExtractionResult, Location, Page, Table
from doc_extractor.profiles import loader
from doc_extractor.profiles.matching import match_profile
from doc_extractor.profiles.operations import _normalize, apply_mapping


def result(format="csv", tables=None, pages=None):
    return ExtractionResult(
        "test", "0" * 64, 0, format, "all", "0.1.0", "test", tables=tables or [], pages=pages or []
    )


def cells(values):
    return [
        [Cell(text, Location(page=1, row=i, column=j)) for j, text in enumerate(row, 1)]
        for i, row in enumerate(values, 1)
    ]


def test_fingerprint_mismatched_file_preset_and_required_text():
    profile = loader.load_builtin("preset.csv.generic.v1")
    mismatch = match_profile(profile, result(format="pdf"))
    assert mismatch.matched is False and mismatch.checks == (("file_format", False),)
    assert match_profile(profile, result()).matched is True

    base = loader.load_file(
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    with_text = replace(base, match={"required_text": ["A Research", "missing"]}, file_format="pdf")
    status = match_profile(with_text, result(format="pdf", pages=[Page(1, "a research paper")]))
    assert not status.matched and status.checks[0][1] is True and status.checks[1][1] is False
    assert not match_profile(replace(base, match={}), result()).matched


def test_fingerprint_headers_reject_blank_or_duplicate_and_accept_extra():
    base = loader.load_file(
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    table_empty = Table("empty", [], Location(), header=True)
    table_duplicate = Table("dup", cells([["A", "A"], ["1", "2"]]), Location())
    table_wrong = Table("wrong", cells([["Other", "X"], ["1", "2"]]), Location())
    table_ok = Table("good", cells([["Datum", "Betrag", "Beschreibung", "Extra"]]), Location())
    assert not match_profile(
        base, result(tables=[table_empty, table_duplicate, table_wrong])
    ).matched
    assert match_profile(base, result(tables=[table_empty, table_duplicate, table_ok])).matched


@pytest.mark.parametrize(
    "raw,settings,out",
    [
        (None, {"type": "decimal"}, (None, None)),
        (" ", {"type": "date", "format": "%Y-%m-%d"}, (None, None)),
        ("2026-01-01", {"type": "date", "format": "%Y-%m-%d"}, ("2026-01-01", "date")),
        ("+12", {"type": "decimal"}, ("12", "decimal")),
        ("-2,000.75", {"type": "decimal"}, ("-2000.75", "decimal")),
        (
            "1\u00a0000,00",
            {"type": "decimal", "decimal_separator": ",", "thousands_separator": " "},
            ("1000.00", "decimal"),
        ),
        # Amounts below 1 printed without a leading zero (e.g. "-.02", ".00").
        ("-.02", {"type": "decimal"}, ("-0.02", "decimal")),
        (".00", {"type": "decimal"}, ("0.00", "decimal")),
        ("+.5", {"type": "decimal"}, ("0.5", "decimal")),
        (
            ",50",
            {"type": "decimal", "decimal_separator": ",", "thousands_separator": "."},
            ("0.50", "decimal"),
        ),
    ],
)
def test_normalizations_preserve_valid_source(raw, settings, out):
    assert _normalize(raw, settings) == out


@pytest.mark.parametrize(
    "raw,settings,message",
    [
        ("€100", {"type": "decimal"}, "syntax"),
        (
            "1,000,000",
            {"type": "decimal", "decimal_separator": ",", "thousands_separator": "."},
            "More than one",
        ),
        (
            "1.234,56",
            {"type": "decimal", "decimal_separator": ".", "thousands_separator": ","},
            "decimal grouping",
        ),
        ("123", {"type": "integer"}, "Unsupported normalization"),
        (".", {"type": "decimal"}, "syntax"),
        ("-.", {"type": "decimal"}, "syntax"),
        (",02", {"type": "decimal"}, "thousands grouping"),
        ("bad date", {"type": "date", "format": "%d.%m.%Y"}, "does not match"),
    ],
)
def test_normalization_failures_are_conservative(raw, settings, message):
    with pytest.raises(ValueError, match=message):
        _normalize(raw, settings)


def test_mapping_skips_unknown_tables_and_partial_rows():
    profile = loader.load_file(
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    res = result(
        tables=[
            Table("empty", [], Location()),
            Table("duplicate", cells([["Datum", "Datum", "Betrag"], ["A", "B", "3"]]), Location()),
            Table("headerless", cells([["A", "B", "C"]]), Location()),
            Table(
                "target",
                cells(
                    [
                        ["Datum", "Beschreibung", "Betrag"],
                        ["", "", ""],
                        ["01/11/2026", "Text"],  # no amount cell
                        ["02/11/2026", "Some text", None],
                    ]
                ),
                Location(),
            ),
        ]
    )
    apply_mapping(profile, res)
    assert "INCOMPLETE_ROW" in [issue.code for issue in res.issues]
    assert len(res.record_sets) == 1
    assert len(res.record_sets[0].records) == 1
    assert res.record_sets[0].records[0]["amount_raw"].raw is None


def test_no_mapping_and_missing_table_branches():
    preset = loader.load_builtin("preset.csv.generic.v1")
    res = result()
    apply_mapping(preset, res)
    assert not res.record_sets and not res.issues
    source = loader.load_file(
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    apply_mapping(source, res)
    assert "LAYOUT_MISMATCH" in {issue.code for issue in res.issues}


def test_mapping_supports_source_column_parsing_fallback():
    source = loader.load_file(
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    pipeline = [dict(op) for op in source.pipeline]
    pipeline[-1] = dict(
        pipeline[-1],
        params={
            "column_mapping": {
                "Datum": "date_raw",
                "Beschreibung": "description_raw",
                "Betrag": "amount_raw",
            },
            "optional_parsing": {"Datum": {"type": "date", "format": "%d/%m/%Y"}},
        },
    )
    source = replace(source, pipeline=tuple(pipeline))
    res = result(
        tables=[
            Table(
                "table",
                cells(
                    [
                        ["Datum", "Beschreibung", "Betrag"],
                        ["01/11/2026", "A", "23"],
                    ]
                ),
                Location(),
            )
        ]
    )
    apply_mapping(source, res)
    assert res.record_sets[0].records[0]["date_raw"].normalized == "2026-11-01"
