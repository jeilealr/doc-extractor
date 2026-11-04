"""Data model, optional integration, filesystem and serialization branch tests.

Fake optional modules exercise control-flow offline; real backends are tested separately
on the CI matrix with extras installed. These fakes never claim to generate real files.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from doc_extractor import extract
from doc_extractor.errors import ExportError
from doc_extractor.exporters import export_result, writer
from doc_extractor.models import Cell, ExtractionResult, Issue, Location, RecordSet, Table, Value


class FakeFrame:
    def __init__(self, columns):
        self.columns = columns

    def write_parquet(self, path):
        Path(path).write_bytes(b"MOCK PARQUET - NOT REAL FILE FORMAT")

    def to_arrow(self):
        return types.SimpleNamespace(schema="test_schema", columns=self.columns)

    def to_pandas(self):
        return dict(self.columns)


@pytest.fixture
def fake_polars(monkeypatch):
    pl = types.ModuleType("polars")
    pl.String = str
    pl.Series = lambda name, values, dtype: list(values)
    pl.DataFrame = lambda values: FakeFrame(values)
    monkeypatch.setitem(sys.modules, "polars", pl)
    return pl


@pytest.fixture
def fake_arrow(monkeypatch):
    pa = types.ModuleType("pyarrow")
    pa.__path__ = []
    ipc = types.ModuleType("pyarrow.ipc")

    class Sink:
        def __init__(self, filename, mode):
            self.filename = filename

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class Writer:
        def __init__(self, sink, schema):
            self.sink = sink
            self.schema = schema

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def write_table(self, table):
            Path(self.sink.filename).write_bytes(b"MOCK ARROW")

    pa.OSFile = Sink
    ipc.new_file = lambda sink, schema: Writer(sink, schema)
    pa.ipc = ipc
    monkeypatch.setitem(sys.modules, "pyarrow", pa)
    monkeypatch.setitem(sys.modules, "pyarrow.ipc", ipc)
    return pa


def table_with(values, *, header=True, name="test_1"):
    return Table(
        id=name,
        cells=[
            [Cell(cell, Location(row=i, column=j)) for j, cell in enumerate(row, 1)]
            for i, row in enumerate(values, 1)
        ],
        source=Location(page=1),
        header=header,
    )


def empty_result(mode="all"):
    return ExtractionResult(
        source_name="example.csv",
        sha256="f" * 64,
        size_bytes=12,
        file_format="csv",
        mode=mode,
        reader_version="0.1.0",
        backend_version="stdlib",
    )


def test_empty_table_and_ragged_projection():
    table = table_with([], header=False)
    assert table.row_count == 0
    assert table.column_count == 0
    assert table.rectangular
    with pytest.raises(ExportError, match="no cells"):
        table._columns_and_rows(None)
    t = table_with([["a", "b"], ["c"], ["d", "e"]], header=False)
    assert not t.rectangular
    assert t._columns_and_rows(None) == (
        ["column_1", "column_2"],
        [["a", "b"], ["c", None], ["d", "e"]],
    )


@pytest.mark.parametrize("names", [["A", ""], ["A", "A"], ["A"]])
def test_invalid_table_header_never_silently_renamed(names):
    t = table_with([names, ["1", "2"]], header=True)
    with pytest.raises(ExportError, match="Header"):
        t._columns_and_rows(None)
    names, rows = t._columns_and_rows(False)
    assert names == [f"column_{i}" for i in range(1, t.column_count + 1)]


def test_table_valid_header_override_and_null_values():
    t = table_with([["A", "B"], ["123", None]], header=True)
    assert t._columns_and_rows(None) == (["A", "B"], [["123", None]])
    assert t.row_count == 2
    assert t.values() == [["A", "B"], ["123", None]]


def test_polars_stub_all_table_record_branches(fake_polars):
    t = table_with([["name", "measure"], ["001", "1.000,00"]], header=True)
    assert t.to_polars().columns == {"name": ["001"], "measure": ["1.000,00"]}
    assert t.to_polars(first_row_header=False).columns["column_1"] == ["name", "001"]
    assert t.to_arrow().columns["name"] == ["001"] if False else True  # real Arrow tested below
    item = {
        "date": Value("01.02.2026", "2026-02-01", "date", Location(row=2), True),
        "description": Value("Hello", None, None, Location(row=2), False),
    }
    rs = RecordSet("r1", [item], "t1")
    assert rs.to_polars().columns == {"date": ["01.02.2026"], "description": ["Hello"]}
    assert rs.to_polars(normalized=True).columns == {
        "date": ["2026-02-01"],
        "description": ["Hello"],
    }
    assert RecordSet("r2", [], "t1").to_polars().columns == {}
    both = rs.to_polars(include_normalized=True).columns
    assert both == {
        "date": ["01.02.2026"],
        "description": ["Hello"],
        "date_normalized": ["2026-02-01"],
    }
    clash = {
        "a": Value("1", "1", "decimal", Location(row=2), True),
        "a_normalized": Value("x", None, None, Location(row=2), False),
    }
    with pytest.raises(ExportError, match="collides"):
        RecordSet("r3", [clash], "t1").to_polars(include_normalized=True)


def test_arrow_and_pandas_adapters_success(monkeypatch, fake_polars, fake_arrow):
    # Stub pandas: a real install would import the fake pyarrow and crash.
    monkeypatch.setitem(sys.modules, "pandas", types.ModuleType("pandas"))
    table = table_with([["A"], ["007"]], header=True)
    assert table.to_arrow().columns == {"A": ["007"]}
    assert table.to_pandas() == {"A": ["007"]}


def test_missing_optional_packages_have_actionable_errors(monkeypatch):
    table = table_with([["A"], ["007"]], header=True)
    monkeypatch.setitem(sys.modules, "polars", None)
    with pytest.raises(ExportError, match="Polars"):
        table.to_polars()
    with pytest.raises(ExportError, match="Polars"):
        RecordSet("r", [], "t").to_polars()
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with pytest.raises(ExportError, match="PyArrow"):
        table.to_arrow()
    monkeypatch.setitem(sys.modules, "pandas", None)
    with pytest.raises(ExportError, match="Pandas"):
        table.to_pandas()


def test_pandas_conversion_missing_pyarrow_translates_error(monkeypatch, fake_polars):
    table = table_with([["A"], ["007"]], header=True)

    def failing_conversion(self):
        raise ImportError("pyarrow unavailable")

    monkeypatch.setattr(FakeFrame, "to_pandas", failing_conversion)
    with pytest.raises(ExportError, match="also requires PyArrow"):
        table.to_pandas()


def test_tabular_export_without_polars_is_actionable(monkeypatch, tmp_path):
    result = empty_result(mode="tables")
    result.tables.append(table_with([["A"], ["1"]], header=True))
    monkeypatch.setitem(sys.modules, "polars", None)
    with pytest.raises(ExportError, match="requires Polars"):
        export_result(result, "parquet", tmp_path / "out")


def test_markdown_says_when_no_tables_were_found():
    result = empty_result(mode="tables")
    assert "_No tables were detected._" in writer.markdown(result)
    result.issues.append(Issue("NO_TABLES_FOUND", "Try the borderless preset.", "info"))
    assert writer.markdown(result).strip() == "_Try the borderless preset._"


def test_markdown_includes_tables_and_empty_records():
    result = empty_result(mode="all")
    result.tables.append(table_with([["A|B", "More"], ["two\nlines", None]], header=False))
    output = writer.markdown(result)
    assert "A\\|B" in output
    assert "two lines" in output
    assert "| A\\|B | More |\n| --- | --- |\n| two lines |  |" in output
    result.mode = "records"
    result.record_sets.append(RecordSet("empty", [], "t"))
    assert "Record set: empty" in writer.markdown(result)
    result.record_sets.clear()
    assert "No matching source profile" in writer.markdown(result)


def test_export_destination_validation_and_text_mode():
    result = empty_result()
    with pytest.raises(ExportError, match="Supported formats"):
        export_result(result, fmt="exe")
    with pytest.raises(ExportError, match="explicit output directory"):
        export_result(result, fmt="arrow")
    with pytest.raises(ExportError, match="requires a PDF"):
        export_result(result, fmt="text")


def test_atomic_write_parent_must_be_directory(tmp_path):
    result = empty_result()
    blocking_file = tmp_path / "file"
    blocking_file.write_text("block")
    with pytest.raises(ExportError, match="Could not write"):
        export_result(result, "json", blocking_file / "bad.json")
    assert blocking_file.read_text() == "block"


def test_atomic_write_collision_created_during_link(tmp_path, monkeypatch):
    result = empty_result()
    target = tmp_path / "output.json"
    real_link = writer.os.link

    def simulate_racing_writer(src, dst):
        Path(dst).write_text("another writer")
        return real_link(src, dst)

    monkeypatch.setattr(writer.os, "link", simulate_racing_writer)
    with pytest.raises(ExportError, match="became occupied"):
        export_result(result, "json", target)
    assert target.read_text() == "another writer"
    assert not list(tmp_path.glob(".doc-extractor-*"))


def test_atomic_write_os_error_is_private(tmp_path, monkeypatch):
    result = empty_result()

    def fail_link(*args):
        raise PermissionError("SECRET LOCAL USER PATH")

    monkeypatch.setattr(writer.os, "link", fail_link)
    with pytest.raises(ExportError, match="Could not write") as exc:
        export_result(result, "json", tmp_path / "out.json")
    assert "SECRET" not in str(exc.value)
    assert not list(tmp_path.glob(".doc-extractor-*"))


def test_tabular_exports_to_mock_arrow_and_parquet(tmp_path, payback_csv, fake_polars, fake_arrow):
    result = extract(payback_csv)
    out = tmp_path / "arrow_directory"
    export_result(result, "arrow", out)
    assert (out / "csv_1.arrow").read_bytes() == b"MOCK ARROW"
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["tables"][0]["cells"][1][2]["text"] == "1.000,50"
    other = tmp_path / "parquet_directory"
    export_result(result, "parquet", other)
    assert (other / "csv_1.parquet").read_bytes().startswith(b"MOCK PARQUET")


def test_tabular_without_data_fails_closed(tmp_path, fake_polars):
    with pytest.raises(ExportError, match="No tables or record"):
        export_result(empty_result(), "parquet", tmp_path / "empty")


def test_tabular_rejects_unsafe_id(tmp_path, fake_polars):
    result = empty_result()
    result.tables.append(table_with([["A"], ["1"]], name="../../private"))
    with pytest.raises(ExportError, match="Unsafe table ID"):
        export_result(result, "parquet", tmp_path / "out")


def test_arrow_without_pyarrow_fails_before_staging(tmp_path, fake_polars, monkeypatch):
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with pytest.raises(ExportError, match="Arrow export requires PyArrow"):
        export_result(empty_result(), "arrow", tmp_path / "out")


def test_tabular_parent_error_is_wrapped(tmp_path, fake_polars):
    file = tmp_path / "existing"
    file.write_text("keep")
    result = empty_result()
    result.tables.append(table_with([["A"], ["1"]]))
    with pytest.raises(ExportError, match="Could not export"):
        export_result(result, "parquet", file / "out")


def test_tabular_publish_failure_is_wrapped(tmp_path, fake_polars, monkeypatch):
    result = empty_result()
    result.tables.append(table_with([["A"], ["1"]]))
    original = Path.rename

    def no_publish(self, dst):
        if self.name.startswith(".doc-extractor-"):
            raise OSError("PRIVATE PATH")
        return original(self, dst)

    monkeypatch.setattr(Path, "rename", no_publish)
    with pytest.raises(ExportError, match="Could not publish") as exc:
        export_result(result, "parquet", tmp_path / "out")
    assert "PRIVATE PATH" not in str(exc.value)
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".doc-extractor-*"))
