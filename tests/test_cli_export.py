from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from doc_extractor import extract
from doc_extractor.cli import main
from doc_extractor.errors import ExportError
from doc_extractor.exporters import export_result


def test_cli_inspect_and_profiles(capsys, sample_pdf):
    assert main(["inspect", str(sample_pdf)]) == 0
    obj = json.loads(capsys.readouterr().out)
    assert obj["format"] == "pdf"
    assert obj["page_count"] == 2
    assert "A Research Paper" not in str(obj)
    assert main(["profiles", "list"]) == 0
    obj = json.loads(capsys.readouterr().out)
    assert "preset.csv.generic.v1" in obj["built_in_presets"]


def test_cli_content_to_file_and_refuses_overwrite(tmp_path, sample_pdf, capsys):
    dest = tmp_path / "output.md"
    assert (
        main(
            [
                "extract",
                str(sample_pdf),
                "--mode",
                "content",
                "--to",
                "markdown",
                "--output",
                str(dest),
            ]
        )
        == 0
    )
    assert "Tpyographic Errror" in dest.read_text()
    assert (
        main(
            [
                "extract",
                str(sample_pdf),
                "--mode",
                "content",
                "--to",
                "markdown",
                "--output",
                str(dest),
            ]
        )
        == 2
    )
    assert "already exists" in capsys.readouterr().err


def test_cli_records_exit_needs_review(tmp_path, capsys):
    p = tmp_path / "unknown.csv"
    p.write_text("A,B\nx,y\n")
    assert main(["extract", str(p), "--mode", "records"]) == 3
    doc = json.loads(capsys.readouterr().out)
    assert {i["code"] for i in doc["issues"]} >= {"PROFILE_REQUIRED", "NO_VALIDATED_RECORDS"}


def test_cli_records_with_profile(payback_csv, capsys):
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    assert (
        main(["extract", str(payback_csv), "--mode", "records", "--profile-file", str(profile)])
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["record_sets"][0]["records"][0]["amount_raw"]["normalized"] == "1000.50"


def test_cli_profiles_explain(payback_csv, capsys):
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    assert main(["profiles", "explain", str(payback_csv), "--profile-file", str(profile)]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["matched"] is True
    assert "Book purchase" not in str(data)


def test_output_symlink_refused(tmp_path, sample_pdf):
    out = tmp_path / "output.json"
    target = tmp_path / "other.json"
    target.write_text("secret")
    out.symlink_to(target)
    with pytest.raises(ExportError, match="already exists"):
        export_result(extract(sample_pdf, mode="content"), "json", out)
    assert target.read_text() == "secret"


def test_pandas_polars_optional_error(tmp_path, payback_csv):
    table = extract(payback_csv).tables[0]
    try:
        import polars  # noqa: F401
    except ImportError:
        with pytest.raises(ExportError, match="Polars"):
            table.to_polars()


def test_arrow_optional_dependency_error(tmp_path, payback_csv):
    result = extract(payback_csv)
    try:
        import polars  # noqa: F401
    except ImportError:
        with pytest.raises(ExportError, match="Polars"):
            export_result(result, "parquet", tmp_path / "new_dir")


def test_cli_python_module_entrypoint_works(sample_pdf):
    cmd = [sys.executable, "-m", "doc_extractor", "inspect", str(sample_pdf)]
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout)["page_count"] == 2


def test_unknown_extension_and_no_output_override(tmp_path, sample_pdf):
    path = tmp_path / "sample.txt"
    path.write_text("hello")
    assert main(["inspect", str(path)]) == 2
    assert main(["extract", str(sample_pdf), "--to", "parquet"]) == 2
