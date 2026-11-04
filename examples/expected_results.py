"""The documented command of every example and the file holding its expected output.

``tests/test_examples.py`` runs each command and compares the output with the file in the
example's ``results/`` folder, so the examples and their READMEs cannot silently go stale.
Refresh the files after an intended change with::

    python examples/make_demo_data.py --results
"""

from __future__ import annotations

import contextlib
import io
import shlex
from dataclasses import dataclass
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parent
ROOT = EXAMPLES.parent


@dataclass(frozen=True)
class Case:
    example: str
    result: str
    command: str  # exactly as documented in the example README, run from the repo root
    exit_code: int = 0

    @property
    def path(self) -> Path:
        return EXAMPLES / self.example / "results" / self.result

    @property
    def argv(self) -> list[str]:
        words = shlex.split(self.command)
        assert words[0] == "doc-extractor", self.command
        return words[1:]


E = "examples"
# fmt: off
CASES = [
    Case("01_quickstart", "narrative_content.md",
         f"doc-extractor extract {E}/01_quickstart/data/demo_narrative.pdf"
         " --mode content --to markdown"),
    Case("01_quickstart", "ruled_records.md",
         f"doc-extractor extract {E}/01_quickstart/data/demo_ruled.pdf --mode records"
         f" --profile-file {E}/01_quickstart/ruled_table_demo_pdf.yaml --to markdown"),
    Case("01_quickstart", "csv_records.md",
         f"doc-extractor extract {E}/01_quickstart/data/demo.csv --mode records"
         f" --profile-file {E}/01_quickstart/payback_activity_csv.yaml --to markdown"),
    Case("02_research_note", "content.txt",
         f"doc-extractor extract {E}/02_research_note/data/demo_research_note.pdf"
         " --mode content --to text"),
    Case("02_research_note", "tables.md",
         f"doc-extractor extract {E}/02_research_note/data/demo_research_note.pdf"
         " --mode tables --to markdown"),
    Case("03_bank_statement_pdf", "tables.md",
         f"doc-extractor extract {E}/03_bank_statement_pdf/data/demo_statement.pdf"
         " --mode tables --to markdown"),
    Case("03_bank_statement_pdf", "records.md",
         f"doc-extractor extract {E}/03_bank_statement_pdf/data/demo_statement.pdf --mode records"
         f" --profile-file {E}/03_bank_statement_pdf/northwind_statement_pdf.yaml --to markdown"),
    Case("04_bank_csv_export", "tables.md",
         f"doc-extractor extract {E}/04_bank_csv_export/data/demo_bank_export.csv --mode tables"
         " --encoding cp1252 --to markdown"),
    Case("04_bank_csv_export", "records.md",
         f"doc-extractor extract {E}/04_bank_csv_export/data/demo_bank_export.csv --mode records"
         f" --profile-file {E}/04_bank_csv_export/bank_export_csv.yaml --to markdown"),
    Case("06_borderless_invoice", "borderless_tables.md",
         f"doc-extractor extract {E}/06_borderless_invoice/data/demo_invoice.pdf --mode tables"
         " --preset preset.pdf.tables.borderless.v1 --to markdown"),
    Case("06_borderless_invoice", "header_table_records.md",
         f"doc-extractor extract {E}/06_borderless_invoice/data/demo_invoice.pdf --mode records"
         f" --profile-file {E}/06_borderless_invoice/invoice_pdf.yaml --to markdown"),
    Case("08_statement_without_lines", "tables.md",
         f"doc-extractor extract {E}/08_statement_without_lines/data/demo_lineless_statement.pdf"
         f" --mode tables --profile-file {E}/08_statement_without_lines/lineless_statement_pdf.yaml"
         " --to markdown"),
]
# fmt: on


def run(case: Case) -> tuple[int, str]:
    """Run the CLI in-process from the repository root; return (exit code, stdout)."""
    import os

    from doc_extractor.cli import main

    buffer = io.StringIO()
    previous = Path.cwd()
    os.chdir(ROOT)
    try:
        with contextlib.redirect_stdout(buffer):
            code = main(case.argv)
    finally:
        os.chdir(previous)
    return code, buffer.getvalue()


def write_all() -> list[Path]:
    written = []
    for case in CASES:
        code, output = run(case)
        if code != case.exit_code:
            raise SystemExit(
                f"{case.example}/{case.result}: exit {code}, expected {case.exit_code}"
            )
        case.path.parent.mkdir(parents=True, exist_ok=True)
        case.path.write_text(output, encoding="utf-8")
        written.append(case.path)
    return written
