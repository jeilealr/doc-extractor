"""Boundary tests for the untrusted YAML configuration surface."""

from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from doc_extractor.errors import DocumentReadError, ProfileError
from doc_extractor.profiles import loader
from doc_extractor.profiles.loader import _check_safe_tree, _operation, from_bytes


def doc(kind="source", fmt="csv"):
    collect = "csv.collect_raw_rows" if fmt == "csv" else "pdf.detect_tables"
    return {
        "profile_schema_version": 1,
        "id": "bank.test.v1" if kind == "source" else "preset.test.v1",
        "version": "1.0.0",
        "kind": kind,
        "format": fmt,
        "match": {"required_headers": ["A", "B"]} if kind == "source" else {},
        "pipeline": [
            {"op": collect, "as": "raw", "params": {}},
            *(
                [
                    {
                        "op": "table.map_columns",
                        "as": "mapped",
                        "input": "raw",
                        "params": {"column_mapping": {"A": "alpha", "B": "beta"}},
                    }
                ]
                if kind == "source"
                else []
            ),
        ],
    }


def decode(data):
    return from_bytes(yaml.safe_dump(data, allow_unicode=True).encode(), source="test")


def op_config(op_name="pdf.detect_tables", params=None, alias="raw"):
    return {"op": op_name, "as": alias, "params": params or {}}


def make_nested(depth):
    item = "x"
    for _ in range(depth):
        item = [item]
    return item


def test_nested_yaml_tree_bounds_and_unhandled_scalar():
    with pytest.raises(ProfileError, match="nesting"):
        _check_safe_tree(make_nested(18))
    with pytest.raises(ProfileError, match="standard"):
        _check_safe_tree(object())
    with pytest.raises(ProfileError, match="elements"):
        _check_safe_tree(["entry"] * 2001)
    shared = ["a"]
    with pytest.raises(ProfileError, match="Recursive or reused"):
        _check_safe_tree([shared, shared])


@pytest.mark.parametrize(
    "raw,error",
    [
        ({}, "Unsupported operation"),
        ({"op": "pdf.collect_text_blocks", "as": "x"}, "not compatible"),
        ({"op": "csv.collect_raw_rows", "as": "x"}, "not compatible"),
        ({"op": "pdf.detect_tables", "as": "bad-name"}, "unique identifier"),
        ({"op": "pdf.detect_tables", "as": "x", "input": "missing"}, "previous"),
        ({"op": "pdf.detect_tables", "as": "x", "input": "x"}, "itself"),
        (
            {"op": "pdf.detect_tables", "as": "x", "params": {"first_row_header": True}},
            "Unsupported parameter",
        ),
        (
            {"op": "pdf.detect_tables", "as": "x", "params": {"preserve_raw_cells": False}},
            "source-fidelity",
        ),
        (
            {"op": "pdf.collect_text_blocks", "as": "x", "params": {"preserve_raw": False}},
            "source-fidelity",
        ),
        (
            {
                "op": "pdf.collect_text_blocks",
                "as": "x",
                "params": {"include_page_and_bbox": False},
            },
            "source-fidelity",
        ),
        (
            {"op": "pdf.detect_tables", "as": "x", "params": {"include_cell_bbox": False}},
            "source-fidelity",
        ),
        (
            {"op": "pdf.detect_tables", "as": "x", "params": {"min_words_vertical": 0}},
            "Invalid PDF table",
        ),
        (
            {"op": "pdf.detect_tables", "as": "x", "params": {"vertical_strategy": "random"}},
            "Unsupported PDF",
        ),
        ({"op": "pdf.detect_tables", "as": "x", "params": {"snap_tolerance": -1}}, "Invalid PDF"),
        (
            {"op": "pdf.detect_tables", "as": "x", "params": {"snap_tolerance": "two"}},
            "Invalid PDF",
        ),
        ({"op": "pdf.detect_tables", "as": "x", "params": {"unknown": True}}, "Unknown keys"),
        ({"op": "pdf.detect_tables", "as": "x", "params": []}, "mapping"),
    ],
)
def test_invalid_operations(raw, error):
    if raw.get("op") == "pdf.collect_text_blocks" and "not compatible" in error:
        fmt = "csv"
    elif raw.get("op") == "csv.collect_raw_rows":
        fmt = "pdf"
    else:
        fmt = "pdf"
    with pytest.raises((ProfileError, DocumentReadError), match=error):
        _operation(raw, fmt, set())


@pytest.mark.parametrize(
    "params,problem",
    [
        ({"encoding": "utf-16"}, "encoding"),
        ({"delimiter": "//"}, "delimiter"),
        ({"first_row_header": "true"}, "boolean"),
        ({"infer_types": True}, "source-fidelity"),
        ({"keep_raw_cell_strings": False}, "source-fidelity"),
        ({"include_row_and_column": False}, "source-fidelity"),
    ],
)
def test_csv_operation_validation(params, problem):
    with pytest.raises(ProfileError, match=problem):
        _operation(op_config("csv.collect_raw_rows", params), "csv", set())


@pytest.mark.parametrize(
    "params,problem",
    [
        ({}, "column_mapping"),
        ({"column_mapping": {}}, "column_mapping"),
        ({"column_mapping": {"A": "x", "B": "x"}}, "column_mapping"),
        ({"column_mapping": {"A": 1}}, "column_mapping"),
        ({"column_mapping": {"A": "x"}, "optional_parsing": []}, "optional_parsing"),
        (
            {"column_mapping": {"A": "x"}, "optional_parsing": {"missing": {"type": "date"}}},
            "unknown field",
        ),
        ({"column_mapping": {"A": "x"}, "optional_parsing": {"x": []}}, "mapping"),
        (
            {"column_mapping": {"A": "x"}, "optional_parsing": {"x": {"type": "integer"}}},
            "Only date",
        ),
        (
            {
                "column_mapping": {"A": "x"},
                "optional_parsing": {"x": {"type": "date", "format": "%m/%d/%Y"}},
            },
            "Unsupported date",
        ),
        (
            {
                "column_mapping": {"A": "x"},
                "optional_parsing": {
                    "x": {"type": "decimal", "decimal_separator": ",", "thousands_separator": ","}
                },
            },
            "decimal separators",
        ),
        (
            {
                "column_mapping": {"A": "x"},
                "optional_parsing": {"x": {"type": "decimal", "decimal_separator": 1}},
            },
            "decimal separators",
        ),
    ],
)
def test_column_mapping_operation_validation(params, problem):
    with pytest.raises(ProfileError, match=problem):
        _operation(op_config("table.map_columns", params), "csv", set())


def test_operation_alias_uniqueness_and_non_table_input():
    used = {"first"}
    with pytest.raises(ProfileError, match="unique"):
        _operation(op_config(alias="first"), "pdf", used)
    with pytest.raises(ProfileError, match="previous"):
        _operation({"op": "pdf.detect_tables", "as": "x", "input": 5}, "pdf", set())


@pytest.mark.parametrize(
    "mutator,problem",
    [
        (lambda x: x.update({"bogus": 1}), "Unknown keys"),
        (lambda x: x.update({"id": "?"}), "Invalid profile ID"),
        (lambda x: x.update({"id": 123}), "Invalid profile ID"),
        (lambda x: x.update({"version": ""}), "Invalid profile version"),
        (lambda x: x.update({"version": ["1"]}), "Invalid profile version"),
        (lambda x: x.update({"kind": "unknown"}), "kind must"),
        (lambda x: x.update({"format": "xml"}), "kind must"),
        (lambda x: x.update({"status": "planned"}), "not runnable"),
        (lambda x: x.update({"match": {}}), "conservative fingerprint"),
        (lambda x: x.update({"match": {"required_text": []}}), "nonempty list"),
        (lambda x: x.update({"match": {"required_text": ["A"]}}), "at least two"),
        (lambda x: x.update({"match": {"bad": ["A", "B"]}}), "Unknown keys"),
        (lambda x: x.update({"match": "name"}), "mapping"),
        (lambda x: x.update({"pipeline": []}), "1 to 12"),
        (lambda x: x.update({"pipeline": [None]}), "mapping"),
        (lambda x: x.update({"pipeline": [op_config("pdf.detect_tables")]}), "not compatible"),
        (
            lambda x: x.update(
                {"pipeline": [{"op": "csv.collect_raw_rows", "as": "raw", "params": {}}]}
            ),
            "must include",
        ),
        (lambda x: x["pipeline"][1].update({"input": "missing"}), "previous"),
        (lambda x: x["pipeline"][1].update({"input": "mapped"}), "itself"),
        (
            lambda x: x["pipeline"][1].update({"input": "raw", "op": "pdf.detect_tables"}),
            "not compatible",
        ),
        (lambda x: x.update({"output": {"kind": "nonsense"}}), "output kind"),
        (lambda x: x.update({"validation": {"bad": True}}), "Unknown keys"),
    ],
)
def test_bad_profiles_fail_conservatively(mutator, problem):
    data = doc()
    mutator(data)
    with pytest.raises((ProfileError, DocumentReadError), match=problem):
        decode(data)


def test_pipeline_dependency_guard_and_duplicates():
    data = doc()
    data["pipeline"][1]["input"] = "raw"
    data["pipeline"][0] = {"op": "pdf.collect_text_blocks", "as": "raw"}
    data["format"] = "pdf"
    with pytest.raises(ProfileError, match="table-producing"):
        decode(data)
    data = doc()
    data["pipeline"].append(copy.deepcopy(data["pipeline"][1]))
    data["pipeline"][2]["as"] = "mapped2"
    with pytest.raises(ProfileError, match="only one table.map_columns"):
        decode(data)
    data = doc(kind="preset", fmt="pdf")
    data["pipeline"].append(op_config(alias="other"))
    with pytest.raises(ProfileError, match="Only one PDF table strategy"):
        decode(data)
    data = doc(kind="preset", fmt="csv")
    data["pipeline"].append(op_config("csv.collect_raw_rows", alias="other"))
    with pytest.raises(ProfileError, match="Only one CSV reading step"):
        decode(data)
    data = doc(kind="preset", fmt="pdf")
    data["pipeline"][0]["input"] = "dummy"
    with pytest.raises(ProfileError, match="previous"):
        decode(data)
    data = doc(kind="preset", fmt="pdf")
    data["pipeline"] = [
        {"op": "pdf.collect_text_blocks", "as": "text", "params": {}},
        {"op": "pdf.detect_tables", "as": "grid", "input": "text", "params": {}},
    ]
    with pytest.raises(ProfileError, match="does not support"):
        decode(data)


def test_non_source_preset_works_and_output_kind_options():
    for output_kind in ("tables", "records", "document", "document_with_tables"):
        data = doc(kind="preset", fmt="csv")
        data["output"] = {"kind": output_kind}
        result = decode(data)
        assert result.kind == "preset"


def test_unknown_preset_and_uninstalled_profile():
    with pytest.raises(ProfileError, match="Unknown bundled"):
        loader.load_builtin("does-not-exist")
    with pytest.raises(ProfileError, match="not installed"):
        loader.load_installed("does-not-exist")


def test_installed_plugin_failure_paths(monkeypatch):
    class BrokenPlugin:
        name = "bad-id"

        def load(self):
            raise RuntimeError("simulated plugin crash")

    class WrongProfile:
        name = "wrong-id"

        def load(self):
            return lambda: "not a Profile"

    class DifferentID:
        name = "different-id"

        def load(self):
            return lambda: replace(loader.load_builtin("preset.csv.generic.v1"), id="other")

    for plugin, problem in (
        (BrokenPlugin(), "failed to load"),
        (WrongProfile(), "invalid profile"),
        (DifferentID(), "invalid profile"),
    ):
        monkeypatch.setattr(
            loader.metadata, "entry_points", lambda plugin=plugin, **kwargs: [plugin]
        )
        with pytest.raises(ProfileError, match=problem):
            loader.load_installed(plugin.name)


def test_file_profile_size_and_filesystem_errors(tmp_path, monkeypatch):
    p = tmp_path / "large.yaml"
    p.write_bytes(b"x" * (loader.MAX_YAML_BYTES + 1))
    with pytest.raises(ProfileError, match="128 KiB"):
        loader.load_file(p)
    file = tmp_path / "normal.yaml"
    file.write_text("profile_schema_version: 1\n")
    real_open = Path.open

    def no_access(self, *args, **kwargs):
        if self == file:
            raise PermissionError("private path")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_access)
    with pytest.raises(ProfileError, match="Unable to read") as err:
        loader.load_file(file)
    assert "private path" not in str(err.value)


def test_bad_yaml_and_collection_aliases():
    with pytest.raises(ProfileError, match="Malformed YAML"):
        from_bytes(b"[unterminated", source="test")
    with pytest.raises(ProfileError, match="mapping"):
        from_bytes(b"[]", source="test")
    with pytest.raises(ProfileError, match="Recursive or reused"):
        from_bytes(b"a: &x [one]\nb: *x", source="test")
