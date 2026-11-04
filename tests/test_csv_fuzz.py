"""Deterministic dialect and quoting coverage, using stdlib CSV as an oracle."""

from __future__ import annotations

import csv
import random

import pytest

from doc_extractor import extract


@pytest.mark.parametrize("delimiter", [",", ";", "\t", "|"])
def test_csv_round_trip_cell_preservation(tmp_path, delimiter):
    rng = random.Random(20261104)
    options = [
        "",
        "hello",
        "00123",
        "Café",
        "a,b",
        "semi;colon",
        "this\nthat",
        "=3+4",
        "1.000,50",
        "0",
        '"wrapped"',
        "weird|pipe",
        "  spaces  ",
    ]
    expected = [[rng.choice(options) for _ in range(3)] for _ in range(50)]
    path = tmp_path / "generated.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerows(expected)
    result = extract(path, delimiter=delimiter, csv_header=False)
    assert result.tables[0].values() == expected
    assert result.tables[0].cells[20][0].source.row == 21
