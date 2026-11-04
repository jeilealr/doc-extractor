"""Contract and error-path coverage for the public API and command-line interface."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from doc_extractor import Limits, api, cli, extract, inspect_file
from doc_extractor.errors import (
    DocumentReadError,
    InputLimitError,
    ProfileError,
    UnsupportedFileError,
)
from doc_extractor.profiles import loader


@pytest.mark.parametrize("mode", ["nonsense", "", None])
def test_unknown_modes_rejected_before_reading(tmp_path, mode):
    with pytest.raises(ValueError, match="mode must be"):
        extract(tmp_path / "missing.pdf", mode=mode)


def test_multiple_selection_options_rejected(payback_csv):
    with pytest.raises(ProfileError, match="at most one"):
        extract(payback_csv, preset="x", profile="y")


def test_api_preset_requires_preset_kind(payback_csv, monkeypatch):
    source = loader.load_file(
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    monkeypatch.setattr(api, "load_builtin", lambda _: source)
    with pytest.raises(ProfileError, match="generic preset"):
        extract(payback_csv, preset="nope")


def test_api_plugin_requires_source_kind(payback_csv, monkeypatch):
    preset = loader.load_builtin("preset.csv.generic.v1")
    monkeypatch.setattr(api, "load_installed", lambda _: preset)
    with pytest.raises(ProfileError, match="source profile"):
        extract(payback_csv, profile="nope")


def test_api_profile_file_wrong_format(payback_csv, ruled_pdf):
    root = Path(__file__).resolve().parents[1]
    with pytest.raises(ProfileError, match="file format"):
        extract(ruled_pdf, profile_file=root / "examples/01_quickstart/payback_activity_csv.yaml")
    with pytest.raises(UnsupportedFileError, match="Content mode"):
        extract(payback_csv, mode="content")


def test_api_overrides_yaml_csv_options(tmp_path):
    f = tmp_path / "example.csv"
    f.write_text("Alpha;Beta\none;two\n")
    result = extract(
        f, preset="preset.csv.generic.v1", delimiter=";", encoding="utf-8", csv_header=False
    )
    assert result.settings["delimiter"] == ";"
    assert result.settings["encoding"] == "utf-8"
    assert result.settings["first_row_header"] is False


def test_version_fallback_and_installed_paths(payback_csv, monkeypatch):
    real = api.metadata.version
    monkeypatch.setattr(api.metadata, "version", lambda _: "9.9.9")
    assert extract(payback_csv).reader_version == "9.9.9"

    def missing(_):
        raise api.metadata.PackageNotFoundError("missing")

    monkeypatch.setattr(api.metadata, "version", missing)
    assert not api._installed()
    assert extract(payback_csv).reader_version == "0.1.0"
    monkeypatch.setattr(api.metadata, "version", real)


def test_inspect_csv_unsniffable_or_undecodable(tmp_path):
    f = tmp_path / "unknown.csv"
    f.write_bytes(b"\xff\xfexyz")
    assert inspect_file(f)["possible_delimiter"] is None
    f.write_text("OnlyOneColumn\n")
    assert inspect_file(f)["possible_delimiter"] is None


def test_inspect_pdf_wraps_unexpected_error(sample_pdf, monkeypatch):
    def broken_open(_):
        raise RuntimeError("PRIVATE DOCUMENT CONTENT HERE")

    monkeypatch.setattr(api.pdfplumber, "open", broken_open)
    with pytest.raises(DocumentReadError, match="Unable to inspect PDF structure") as exc:
        inspect_file(sample_pdf)
    assert "PRIVATE" not in str(exc.value)


def test_inspect_pdf_limit_error_preserved(sample_pdf):
    with pytest.raises(InputLimitError, match="max_pages"):
        inspect_file(sample_pdf, limits=Limits(max_pages=1))


def test_cli_profile_validate_list_and_reject_unsupported(tmp_path, capsys):
    p = Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    assert cli.main(["profiles", "validate", str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True
    assert cli.main(["profiles", "list"]) == 0
    assert "installed_source_profiles" in json.loads(capsys.readouterr().out)
    assert cli.main(["profiles", "validate", str(tmp_path / "missing.yaml")]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_cli_explain_layout_mismatch(tmp_path, capsys):
    p = tmp_path / "unknown.csv"
    p.write_text("Foo,Bar\n1,2\n")
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    assert cli.main(["profiles", "explain", str(p), "--profile-file", str(profile)]) == 3
    body = json.loads(capsys.readouterr().out)
    assert body["matched"] is False
    assert "LAYOUT_MISMATCH" in body["issues"]


def test_cli_csv_overrides_and_strict(tmp_path, capsys):
    file = tmp_path / "semicolon.csv"
    file.write_text("A;B\n1;2\n")
    args = ["extract", str(file), "--delimiter", ";", "--csv-header", "none", "--mode", "tables"]
    assert cli.main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["settings"]["first_row_header"] is False
    assert result["tables"][0]["cells"][0][0]["text"] == "A"
    p = tmp_path / "ragged.csv"
    p.write_text("A,B\n1\n")
    assert cli.main(["extract", str(p), "--strict"]) == 3
    assert "needs review" in capsys.readouterr().err


def test_cli_record_output_and_no_matches(tmp_path, capsys):
    file = tmp_path / "unknown.csv"
    file.write_text("A,B\n1,2\n")
    assert (
        cli.main(
            [
                "extract",
                str(file),
                "--mode",
                "records",
                "--to",
                "parquet",
                "--output",
                str(tmp_path / "dir"),
            ]
        )
        == 3
    )
    assert "No records mapped" in capsys.readouterr().err
    assert cli.main(["extract", str(file), "--mode", "records", "--to", "markdown"]) == 3
    assert "No validated records" in capsys.readouterr().err


def test_cli_broken_stdout(monkeypatch, payback_csv):
    class BadOut:
        def write(self, s):
            raise BrokenPipeError

    monkeypatch.setattr(sys, "stdout", BadOut())
    assert cli.main(["extract", str(payback_csv), "--to", "json"]) == 130


def test_cli_keyboard_interrupt(monkeypatch, payback_csv):
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "extract", interrupt)
    assert cli.main(["extract", str(payback_csv)]) == 130


def test_cli_unknown_dispatch_fails_closed(monkeypatch):
    monkeypatch.setattr(
        cli,
        "make_parser",
        lambda: SimpleNamespace(parse_args=lambda _: SimpleNamespace(command="unknown")),
    )
    assert cli.main([]) == 2


def test_package_module_entrypoint_line_coverage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["doc-extractor", "--version"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("doc_extractor.__main__", run_name="__main__")
    assert exc.value.code == 0
    assert "doc-extractor 0.1.0" in capsys.readouterr().out
