from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from doc_extractor import extract
from doc_extractor.errors import ProfileError
from doc_extractor.profiles import builtin_profile_ids, load_file
from doc_extractor.profiles.loader import from_bytes


def test_all_builtin_presets_are_valid():
    names = builtin_profile_ids()
    assert len(names) >= 5
    assert "preset.pdf.tables.borderless.v1" in names


def test_payback_source_profile_maps_raw_and_normalized(payback_csv):
    from pathlib import Path

    fixture_profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    result = extract(payback_csv, mode="records", profile_file=fixture_profile)
    assert result.profile_id == "banking.payback.de.activity.csv.v1"
    assert result.profile_sha256
    assert len(result.record_sets) == 1
    rows = result.record_sets[0].records
    assert len(rows) == 2
    assert rows[0]["amount_raw"].raw == "1.000,50"
    assert rows[0]["amount_raw"].normalized == "1000.50"
    assert rows[0]["amount_raw"].normalized_type == "decimal"
    assert rows[0]["date_raw"].normalized == "2026-11-02"
    assert rows[0]["amount_raw"].source.row == 2
    assert rows[0]["amount_raw"].source.column == 3
    assert rows[1]["amount_raw"].normalized == "-45.80"


def test_profile_mismatch_never_maps_records(tmp_path):
    from pathlib import Path

    p = tmp_path / "unrelated.csv"
    p.write_text("Date,Amount\n2026-11-04,1000\n")
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    result = extract(p, mode="records", profile_file=profile)
    assert not result.record_sets
    assert {i.code for i in result.issues} >= {"LAYOUT_MISMATCH", "NO_VALIDATED_RECORDS"}
    assert result.tables[0].cells[1][1].text == "1000"


def test_normalization_failure_preserves_raw(tmp_path):
    from pathlib import Path

    p = tmp_path / "activity.csv"
    p.write_text('Datum,Beschreibung,Betrag\n03/11/2026,Book,"1.2.3,00"\n')
    profile = (
        Path(__file__).resolve().parents[1] / "examples/01_quickstart/payback_activity_csv.yaml"
    )
    result = extract(p, mode="records", profile_file=profile)
    val = result.record_sets[0].records[0]["amount_raw"]
    assert val.raw == "1.2.3,00" and val.normalized is None
    assert "NORMALIZATION_FAILED" in {i.code for i in result.issues}


def test_safe_yaml_rejects_python_execution(tmp_path):
    p = tmp_path / "danger.yaml"
    p.write_text("!!python/object/apply:os.system ['touch /tmp/should-not-create']")
    with pytest.raises(ProfileError):
        load_file(p)


def test_unknown_operation_rejected():
    data = b"""
profile_schema_version: 1
id: preset.fake.v1
kind: preset
format: pdf
pipeline:
  - op: shell.execute
    as: bad
    params: {cmd: 'echo attack'}
"""
    with pytest.raises(ProfileError, match="Unsupported operation"):
        from_bytes(data, source="test")


def test_unsupported_design_example_rejected(tmp_path):
    p = tmp_path / "design.yaml"
    p.write_text("""
profile_schema_version: 1
id: banking.fake.pdf.v1
kind: source
format: pdf
status: design_example_requires_python_adapter
match: {required_text: [Bank]}
processor: {kind: registered_python_adapter}
""")
    with pytest.raises(ProfileError, match="design-only profile sketch"):
        load_file(p)


@pytest.mark.parametrize(
    "planned",
    sorted((Path(__file__).resolve().parents[1] / "docs/design/bank-profiles").glob("*.yaml")),
    ids=lambda p: p.name,
)
def test_planned_bank_profiles_explain_why_they_cannot_run(planned):
    with pytest.raises(ProfileError, match="cannot be run.*bank-profiles/README.md"):
        load_file(planned)


def test_cyclic_yaml_rejected():
    with pytest.raises(ProfileError):
        from_bytes(b"a: &a [*a]\n", source="test")


def test_large_yaml_rejected():
    with pytest.raises(ProfileError):
        from_bytes(b"a: " + b"x" * (130 * 1024), source="test")


def test_profile_schema_version_rejected():
    p = b"profile_schema_version: 2\nid: preset.fake.v1\nkind: preset\nformat: pdf\n"
    with pytest.raises(ProfileError):
        from_bytes(p, source="test")


def test_user_defined_pdf_profile_maps_table(ruled_pdf, tmp_path):
    p = tmp_path / "custom_pdf.yaml"
    p.write_text(
        textwrap.dedent("""
        profile_schema_version: 1
        id: test.pdf.invoice.v1
        kind: source
        format: pdf
        match: {required_headers: [Date, Description, Amount]}
        pipeline:
          - op: pdf.collect_text_blocks
            as: blocks
            params: {preserve_raw: true, include_page_and_bbox: true}
          - op: pdf.detect_tables
            as: found
            params: {vertical_strategy: lines, horizontal_strategy: lines}
          - op: table.map_columns
            input: found
            as: records
            params:
              column_mapping: {Date: date, Description: description, Amount: amount}
              optional_parsing:
                date: {type: date, format: '%Y-%m-%d'}
                amount: {type: decimal, decimal_separator: '.', thousands_separator: ','}
        output: {kind: records}
    """)
    )
    result = extract(ruled_pdf, mode="records", profile_file=p)
    assert len(result.record_sets) == 1
    assert len(result.record_sets[0].records) == 2
    assert result.record_sets[0].records[0]["amount"].normalized == "1000.00"
    assert result.record_sets[0].records[0]["amount"].source.bbox is not None
