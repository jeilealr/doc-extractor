"""Regression checks for the final rare control-flow branches."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from doc_extractor import cli, extract
from doc_extractor.errors import ExportError, UnsupportedFileError
from doc_extractor.exporters.writer import _atomic_write
from doc_extractor.profiles import loader
from doc_extractor.profiles.operations import _normalize
from doc_extractor.utils import Limits, read_source


def test_csv_profile_can_omit_all_optional_reader_parameters(tmp_path):
    p = tmp_path / "plain.csv"
    p.write_text("A,B\n1,2\n")
    profile = {
        "profile_schema_version": 1,
        "id": "preset.minimal.csv.v1",
        "version": "1.0.0",
        "kind": "preset",
        "format": "csv",
        "pipeline": [{"op": "csv.collect_raw_rows", "as": "rows", "params": {}}],
    }
    yml = tmp_path / "minimal.yaml"
    yml.write_text(yaml.safe_dump(profile))
    result = extract(p, profile_file=yml)
    assert result.tables[0].values()[1] == ["1", "2"]


def test_profile_registry_ignores_unrelated_resource_files(monkeypatch):
    class Source:
        name = "README.txt"

    class Directory:
        def iterdir(self):
            yield Source()

    class Files:
        def joinpath(self, name):
            assert name == "presets"
            return Directory()

    monkeypatch.setattr(loader.resources, "files", lambda name: Files())
    assert loader._bundled_profiles() == []


def test_registry_skips_non_matching_entry_points(monkeypatch):
    original = loader.load_file(
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )

    class Plugin:
        def __init__(self, name):
            self.name = name

        def load(self):
            return lambda: original

    monkeypatch.setattr(
        loader.metadata, "entry_points", lambda **kwargs: [Plugin("unrelated"), Plugin(original.id)]
    )
    assert loader.load_installed(original.id).id == original.id


def test_decimal_rejects_disguised_invalid_grouping():
    with pytest.raises(ValueError, match="Invalid thousands grouping"):
        _normalize(
            "1234,567", {"type": "decimal", "decimal_separator": ".", "thousands_separator": ","}
        )


def test_nonexistent_input_is_rejected(tmp_path):
    with pytest.raises(UnsupportedFileError, match="existing regular file"):
        read_source(tmp_path / "not_found.csv", Limits())


def test_atomic_write_rechecks_parent_directory(tmp_path, monkeypatch):
    parent = tmp_path / "output"
    target = parent / "new.json"
    real_is_dir = Path.is_dir

    def mutated_parent(self):
        if self == parent:
            return False
        return real_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", mutated_parent)
    with pytest.raises(ExportError, match="not a directory"):
        _atomic_write(target, b"123")
    assert not target.exists()


def test_cli_unknown_profiles_subcommand_falls_through(monkeypatch):
    monkeypatch.setattr(
        cli,
        "make_parser",
        lambda: SimpleNamespace(
            parse_args=lambda _: SimpleNamespace(command="profiles", profiles_command="unknown")
        ),
    )
    assert cli.main([]) == 2


def test_cli_direct_module_code_path(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["doc-extractor", "--version"])
    # The CLI is already imported by other tests; runpy warns about re-execution.
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("doc_extractor.cli", run_name="__main__")
    assert exc.value.code == 0
    assert "doc-extractor" in capsys.readouterr().out
