"""Additional review-path tests targeting security, data loss, and output semantics."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from doc_extractor import Limits, extract
from doc_extractor.cli import main
from doc_extractor.errors import DocumentReadError, ExportError, InputLimitError, ProfileError
from doc_extractor.exporters import export_result
from doc_extractor.profiles.loader import from_bytes
from doc_extractor.readers.pdf_reader import validate_table_settings


def test_unhashable_pdf_table_strategy_is_clean_error():
    with pytest.raises(DocumentReadError):
        validate_table_settings({"vertical_strategy": ["lines"]})


def test_excessively_large_input_detected_early(tmp_path):
    path = tmp_path / "large.csv"
    path.write_bytes(b"X" * 2048)
    with pytest.raises(InputLimitError):
        extract(path, limits=Limits(max_bytes=100))


def test_source_profile_single_anchor_fails_closed():
    yaml = b"""
profile_schema_version: 1
id: source.weak.v1
kind: source
format: csv
match: {required_headers: [Amount]}
pipeline:
  - op: csv.collect_raw_rows
    as: rows
    params: {}
  - op: table.map_columns
    as: mapped
    input: rows
    params: {column_mapping: {Amount: amount}}
"""
    with pytest.raises(ProfileError, match="at least two"):
        from_bytes(yaml, source="test")


def test_yaml_disallows_unsafe_parameter_types():
    yaml = b"""
profile_schema_version: 1
id: preset.invalid.v1
kind: preset
format: pdf
pipeline:
  - op: pdf.detect_tables
    as: tables
    params: {vertical_strategy: [lines]}
"""
    with pytest.raises(DocumentReadError):
        from_bytes(yaml, source="test")


def test_normalized_frame_projection_never_inserts_bad_raw_value(tmp_path, monkeypatch):
    class FakePolars:
        String = str

        @staticmethod
        def Series(name, values, dtype):
            return list(values)

        @staticmethod
        def DataFrame(obj):
            return obj

    monkeypatch.setitem(sys.modules, "polars", FakePolars)
    from pathlib import Path

    csv = tmp_path / "activity.csv"
    csv.write_text('Datum,Beschreibung,Betrag\n03/11/2026,Book,"bad.amount"\n')
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    result = extract(csv, mode="records", profile_file=profile)
    frame_raw = result.record_sets[0].to_polars()
    frame_normalized = result.record_sets[0].to_polars(normalized=True)
    assert frame_raw["amount_raw"] == ["bad.amount"]
    assert frame_normalized["amount_raw"] == [None]
    assert frame_normalized["description_raw"] == ["Book"]


def test_table_frame_keeps_text_without_type_guessing(payback_csv, monkeypatch):
    class FakePolars:
        String = str

        @staticmethod
        def Series(name, values, dtype):
            return list(values)

        @staticmethod
        def DataFrame(obj):
            return obj

    monkeypatch.setitem(sys.modules, "polars", FakePolars)
    table = extract(payback_csv).tables[0]
    frame = table.to_polars()
    assert frame["Betrag"] == ["1.000,50", "-45,80"]


def test_record_mode_markdown_not_silent_empty(payback_csv):
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    result = extract(payback_csv, mode="records", profile_file=profile)
    rendered = export_result(result, "markdown")
    assert "amount_raw" in rendered
    assert "1.000,50" in rendered


def test_document_sha_and_profile_version_in_serialized_result(payback_csv):
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    serialized = extract(payback_csv, mode="records", profile_file=profile).to_dict()
    assert serialized["result_schema_version"] == 1
    assert serialized["profile_id"] == "banking.payback.de.activity.csv.v1"
    assert len(serialized["profile_sha256"]) == 64
    assert "limits" in serialized["settings"]


def test_cli_empty_record_parquet_exit_review(tmp_path, capsys):
    csv = tmp_path / "plain.csv"
    csv.write_text("Foo,Bar\n1,2\n")
    ret = main(
        [
            "extract",
            str(csv),
            "--mode",
            "records",
            "--to",
            "parquet",
            "--output",
            str(tmp_path / "missing"),
        ]
    )
    assert ret == 3
    assert "No records mapped" in capsys.readouterr().err
    assert not (tmp_path / "missing").exists()


def test_csv_export_without_tables_does_not_silently_create_parquet(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("\n")
    result = extract(p)
    # We reject missing optional dependencies instead of silently emitting a fake Parquet.
    try:
        import polars  # noqa: F401
    except ImportError:
        with pytest.raises(ExportError):
            export_result(result, "parquet", tmp_path / "out")


def test_text_export_rejects_table_or_record_only_modes(ruled_pdf):
    from doc_extractor.errors import ExportError

    for mode in ("tables", "records"):
        with pytest.raises(ExportError, match="requires a PDF"):
            export_result(extract(ruled_pdf, mode=mode), "text")


def test_records_preset_is_not_a_source_profile(payback_csv):
    result = extract(payback_csv, mode="records", preset="preset.csv.generic.v1")
    assert "PROFILE_REQUIRED" in {issue.code for issue in result.issues}


def test_profile_rejects_invalid_dependency_chain():
    from doc_extractor.profiles.loader import from_bytes

    bad = b"""
profile_schema_version: 1
id: preset.invalid.chain.v1
kind: preset
format: pdf
pipeline:
  - op: pdf.collect_text_blocks
    as: lines
  - op: table.map_columns
    input: lines
    as: mapped
    params: {column_mapping: {Foo: foo}}
"""
    with pytest.raises(ProfileError, match="table-producing"):
        from_bytes(bad, source="test")


def test_profile_validates_encoding_before_input_open():
    from doc_extractor.profiles.loader import from_bytes

    bad = b"""
profile_schema_version: 1
id: preset.invalid.csv.v1
kind: preset
format: csv
pipeline:
  - op: csv.collect_raw_rows
    as: rows
    params: {encoding: rust-python-codec}
"""
    with pytest.raises(ProfileError, match="Unsupported CSV encoding"):
        from_bytes(bad, source="test")


def test_input_file_permission_error_is_sanitized(monkeypatch, tmp_path):
    from doc_extractor import utils

    file = tmp_path / "blocked.csv"
    file.write_text("a,b\n1,2\n")
    original_open = Path.open

    def deny_specific(path, *args, **kwargs):
        if path == file:
            raise PermissionError("private underlying filesystem details")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_specific)
    from doc_extractor.errors import DocumentReadError

    with pytest.raises(DocumentReadError) as err:
        utils.read_source(file, Limits())
    assert "private underlying" not in str(err.value)
