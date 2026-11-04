"""Every documented example command still produces its committed expected output."""

from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
_spec = importlib.util.spec_from_file_location("expected_results", EXAMPLES / "expected_results.py")
expected_results = importlib.util.module_from_spec(_spec)
sys.modules["expected_results"] = expected_results
_spec.loader.exec_module(expected_results)


@pytest.mark.parametrize("case", expected_results.CASES, ids=lambda c: f"{c.example}/{c.result}")
def test_example_output_matches_results(case):
    code, output = expected_results.run(case)
    assert code == case.exit_code
    assert output == case.path.read_text(encoding="utf-8"), (
        "Example output changed; if intended run: python examples/make_demo_data.py --results"
    )


def test_reconcile_script_balances(capsys):
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(
            str(EXAMPLES / "03_bank_statement_pdf" / "reconcile.py"), run_name="__main__"
        )
    assert stop.value.code == 0
    assert "reconciled  yes" in capsys.readouterr().out


def test_lineless_statement_checks_pass(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["check_statement.py"])
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(
            str(EXAMPLES / "08_statement_without_lines" / "check_statement.py"), run_name="__main__"
        )
    output = capsys.readouterr().out
    assert stop.value.code == 0, output
    assert "FAIL" not in output and "2026-01-14" in output


def test_parquet_duckdb_example(tmp_path, capsys, monkeypatch):
    pytest.importorskip("polars")
    pytest.importorskip("duckdb")
    script = EXAMPLES / "05_parquet_and_duckdb" / "query.py"
    monkeypatch.setattr(sys, "argv", [str(script), str(tmp_path / "out")])
    with pytest.raises(SystemExit) as stop:
        runpy.run_path(str(script), run_name="__main__")
    assert stop.value.code == 0
    assert "spending by category" in capsys.readouterr().out
