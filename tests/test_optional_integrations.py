"""Real optional-package integration checks: skipped only when extras aren't installed.

Continuous integration installs [all] so these tests must execute there. The offline
local audit cannot run them because no Polars/DuckDB/PyArrow wheels were available.
"""

from __future__ import annotations

import importlib
import os

import pytest

from doc_extractor import extract
from doc_extractor.exporters import export_result


def optional_module(name: str):
    """CI requires extras; offline core-only installs may skip real integrations."""
    if os.environ.get("DOC_EXTRACTOR_REQUIRE_EXTRAS") == "1":
        return importlib.import_module(name)
    return pytest.importorskip(name)


def test_real_polars_and_parquet(tmp_path, payback_csv):
    pl = optional_module("polars")
    table = extract(payback_csv).tables[0]
    frame = table.to_polars()
    assert frame.shape == (2, 3)
    assert frame.get_column("Betrag").to_list() == ["1.000,50", "-45,80"]
    destination = tmp_path / "parquet_result"
    export_result(extract(payback_csv), "parquet", destination)
    reloaded = pl.read_parquet(destination / "csv_1.parquet")
    assert reloaded.get_column("Betrag").to_list() == ["1.000,50", "-45,80"]


def test_real_arrow_roundtrip(tmp_path, payback_csv):
    pa = optional_module("pyarrow")
    optional_module("polars")
    table = extract(payback_csv).tables[0]
    arrow = table.to_arrow()
    assert arrow.num_rows == 2
    destination = tmp_path / "arrow_result"
    export_result(extract(payback_csv), "arrow", destination)
    with pa.memory_map(str(destination / "csv_1.arrow"), "r") as source:
        reloaded = pa.ipc.open_file(source).read_all()
    assert reloaded.column("Betrag").to_pylist() == ["1.000,50", "-45,80"]


def test_real_duckdb_parquet_query(tmp_path, payback_csv):
    duckdb = optional_module("duckdb")
    optional_module("polars")
    destination = tmp_path / "sql_result"
    export_result(extract(payback_csv), "parquet", destination)
    with duckdb.connect(":memory:") as conn:
        relation = conn.read_parquet(str(destination / "csv_1.parquet"))
        rows = relation.project("Betrag").fetchall()
    assert rows == [("1.000,50",), ("-45,80",)]


def test_real_pandas_optional_adapter(payback_csv):
    pd = optional_module("pandas")
    optional_module("polars")
    optional_module("pyarrow")
    frame = extract(payback_csv).tables[0].to_pandas()
    assert isinstance(frame, pd.DataFrame)
    assert frame["Betrag"].tolist() == ["1.000,50", "-45,80"]


def test_real_parquet_records_keep_raw_and_normalized(tmp_path, payback_csv):
    from pathlib import Path

    pl = optional_module("polars")
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    destination = tmp_path / "records_result"
    export_result(
        extract(payback_csv, mode="records", profile_file=profile), "parquet", destination
    )
    frame = pl.read_parquet(destination / "records_1.parquet")
    assert frame.columns == [
        "date_raw",
        "description_raw",
        "amount_raw",
        "date_raw_normalized",
        "amount_raw_normalized",
    ]
    assert frame.get_column("amount_raw").to_list() == ["1.000,50", "-45,80"]
    assert frame.get_column("amount_raw_normalized").to_list() == ["1000.50", "-45.80"]
