"""Exercise optional export control flow with mocks when binary extras are unavailable.

These tests do NOT claim to validate real Parquet or Arrow serialization.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from doc_extractor import extract
from doc_extractor.errors import ExportError
from doc_extractor.exporters import export_result


class FakeFrame:
    def __init__(self, mapping):
        self.mapping = mapping

    def write_parquet(self, path):
        Path(path).write_bytes(b"FAKE-PARQUET-ONLY-FOR-CONTROL-FLOW")


class FakePolars:
    String = str

    @staticmethod
    def Series(name, values, dtype):
        return list(values)

    @staticmethod
    def DataFrame(mapping):
        return FakeFrame(mapping)


def test_parquet_export_stages_and_writes_manifest(tmp_path, payback_csv, monkeypatch):
    monkeypatch.setitem(sys.modules, "polars", FakePolars)
    result = extract(payback_csv)
    dest = tmp_path / "output"
    assert export_result(result, "parquet", dest) == dest
    assert (dest / "csv_1.parquet").read_bytes().startswith(b"FAKE-PARQUET")
    manifest = json.loads((dest / "manifest.json").read_text())
    assert manifest["sha256"] == result.sha256
    assert manifest["tables"][0]["cells"][1][2]["text"] == "1.000,50"
    assert manifest["settings"]["first_row_header"] is True
    with pytest.raises(ExportError, match="already exists"):
        export_result(result, "parquet", dest)
    assert not list(tmp_path.glob(".doc-extractor-*"))


def test_parquet_records_only_writes_recordset(tmp_path, payback_csv, monkeypatch):
    monkeypatch.setitem(sys.modules, "polars", FakePolars)
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    result = extract(payback_csv, mode="records", profile_file=profile)
    dest = tmp_path / "recorded"
    export_result(result, "parquet", dest)
    assert (dest / "records_1.parquet").is_file()
    assert not (dest / "csv_1.parquet").exists()


def test_parquet_refuses_directory_symlink(tmp_path, payback_csv, monkeypatch):
    monkeypatch.setitem(sys.modules, "polars", FakePolars)
    dest = tmp_path / "linked"
    actual = tmp_path / "existing"
    actual.mkdir()
    dest.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ExportError, match="already exists"):
        export_result(extract(payback_csv), "parquet", dest)
    assert list(actual.iterdir()) == []


def test_plain_markdown_and_json_export_not_empty(sample_pdf, tmp_path):
    result = extract(sample_pdf, mode="content")
    assert "Tpyographic Errror" in export_result(result, "markdown")
    assert "Tpyographic Errror" in export_result(result, "text")
    written = tmp_path / "content.json"
    assert export_result(result, "json", written) == written
    assert json.loads(written.read_text())["pages"][0]["number"] == 1


def test_profile_installed_plugin_discovered_only_when_selected(monkeypatch, payback_csv):
    from doc_extractor.profiles import loader

    profile = loader.load_file(
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    events = []

    class FakeEntryPoint:
        name = profile.id

        def load(self):
            events.append("loaded")
            return lambda: profile

    monkeypatch.setattr(loader.metadata, "entry_points", lambda **kw: [FakeEntryPoint()])
    assert profile.id in loader.installed_profile_ids()
    assert not events
    doc = extract(payback_csv, mode="records", profile=profile.id)
    assert events == ["loaded"]
    assert doc.record_sets
