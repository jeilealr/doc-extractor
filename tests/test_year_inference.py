"""Day-month dates get their year from the statement period printed on the document."""

from __future__ import annotations

from datetime import date

import pytest

from doc_extractor.errors import ProfileError
from doc_extractor.models import Cell, ExtractionResult, Location, Page, Table
from doc_extractor.profiles.loader import _date_settings
from doc_extractor.profiles.operations import _normalize, apply_mapping, find_period

SPEC = {"start_label": "DESDE:", "end_label": "HASTA:", "format": "%Y/%m/%d"}
PERIOD = (date(2025, 12, 31), date(2026, 3, 31))
DAY_MONTH = {"type": "date", "format": "%d/%m", "year_from_period": SPEC}


def test_period_is_read_from_the_words_after_the_labels():
    text = "ESTADO DE CUENTA\nDESDE: 2025/12/31 HASTA: 2026/03/31\nCUENTA"
    assert find_period(text, SPEC) == PERIOD


@pytest.mark.parametrize(
    "text,message",
    [
        ("no period here", "'DESDE:' not found"),
        ("DESDE:", "'DESDE:' not found"),
        ("DESDE: 2026/03/31 HASTA: 2025/12/31", "ends before it starts"),
        ("DESDE: 31.12.2025 HASTA: 2026/03/31", "does not match format"),
    ],
)
def test_period_problems_are_errors(text, message):
    with pytest.raises(ValueError, match=message):
        find_period(text, SPEC)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("31/12", "2025-12-31"),  # December belongs to the start year
        ("14/01", "2026-01-14"),  # January to the next year
        ("31/03", "2026-03-31"),
    ],
)
def test_year_is_the_one_that_places_the_date_inside_the_period(raw, expected):
    assert _normalize(raw, DAY_MONTH, PERIOD) == (expected, "date")


def test_leap_day_and_other_day_month_formats():
    leap = (date(2028, 1, 1), date(2028, 3, 31))
    assert _normalize("29/02", DAY_MONTH, leap) == ("2028-02-29", "date")
    dotted = {"type": "date", "format": "%d.%m.", "year_from_period": SPEC}
    assert _normalize("11.08.", dotted, (date(2026, 8, 10), date(2026, 9, 7))) == (
        "2026-08-11",
        "date",
    )


@pytest.mark.parametrize(
    "raw,period,message",
    [
        ("14/01", None, "period not found"),
        ("15/06", PERIOD, "outside the statement period"),
        ("31/02", PERIOD, "does not match the format"),
        ("14/01", (date(2025, 1, 1), date(2026, 6, 30)), "ambiguous"),
    ],
)
def test_year_inference_never_guesses(raw, period, message):
    with pytest.raises(ValueError, match=message):
        _normalize(raw, DAY_MONTH, period)


def _result(page_text: str) -> ExtractionResult:
    def cell(text, row, col):
        return Cell(text, Location(page=1, row=row, column=col))

    table = Table(
        "t1",
        [[cell("FECHA", 1, 1), cell("VALOR", 1, 2)], [cell("14/01", 2, 1), cell("5.18", 2, 2)]],
        Location(page=1),
        header=True,
    )
    result = ExtractionResult("x.pdf", "0" * 64, 1, "pdf", "records", "0", "0")
    result.pages = [Page(1, page_text)]
    result.tables = [table]
    return result


class _Profile:
    pipeline = (
        {
            "op": "table.map_columns",
            "params": {
                "column_mapping": {"FECHA": "date"},
                "optional_parsing": {"date": DAY_MONTH},
            },
        },
    )


def test_mapping_uses_the_period_from_the_page_text():
    result = _result("DESDE: 2025/12/31 HASTA: 2026/03/31")
    apply_mapping(_Profile, result)
    value = result.record_sets[0].records[0]["date"]
    assert (value.raw, value.normalized) == ("14/01", "2026-01-14")
    assert not result.issues


def test_missing_period_is_reported_once_and_raw_dates_are_kept():
    result = _result("no period on this statement")
    apply_mapping(_Profile, result)
    assert [i.code for i in result.issues] == ["PERIOD_NOT_FOUND", "NORMALIZATION_FAILED"]
    value = result.record_sets[0].records[0]["date"]
    assert (value.raw, value.normalized) == ("14/01", None)


@pytest.mark.parametrize(
    "settings,message",
    [
        ({"format": "%d/%m"}, "has no year"),
        ({"format": "%d/%m", "year_from_period": {**SPEC, "start_label": " "}}, "start_label"),
        ({"format": "%d/%m", "year_from_period": {**SPEC, "format": "%d/%m"}}, "period date"),
        ({"format": "%d/%m", "year_from_period": {**SPEC, "extra": 1}}, "Unknown keys"),
        ({"format": "%d/%m/%Y", "year_from_period": SPEC}, "only applies"),
        ({"format": "%m-%d"}, "Unsupported date format"),
    ],
)
def test_profile_date_settings_are_validated(settings, message):
    with pytest.raises(ProfileError, match=message):
        _date_settings({"type": "date", **settings})


def test_valid_profile_date_settings():
    _date_settings(dict(DAY_MONTH))
    _date_settings({"type": "date", "format": "%Y/%m/%d"})
