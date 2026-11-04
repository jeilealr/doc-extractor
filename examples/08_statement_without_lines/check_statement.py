"""Extract a statement without drawn lines and prove every transaction was read correctly.

The statement prints its own checks: SALDO ANTERIOR, TOTAL ABONOS, TOTAL CARGOS and
SALDO ACTUAL, plus a running SALDO on every row. This script compares all of them with
the extracted rows, using exact Decimal arithmetic.

    python examples/08_statement_without_lines/check_statement.py
    python examples/08_statement_without_lines/check_statement.py my.pdf my_profile.yaml
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal
from pathlib import Path

from doc_extractor import extract

HERE = Path(__file__).resolve().parent
DEFAULT_PDF = HERE / "data" / "demo_lineless_statement.pdf"
DEFAULT_PROFILE = HERE / "lineless_statement_pdf.yaml"


def summary_value(text: str, label: str) -> Decimal:
    match = re.search(re.escape(label) + r"\s+\$\s+(-?[\d,]*\.\d{2})", text)
    if match is None:
        raise SystemExit(f"summary value {label!r} not found")
    return Decimal(match[1].replace(",", ""))


def main(argv: list[str]) -> int:
    pdf = Path(argv[0]) if argv else DEFAULT_PDF
    profile = Path(argv[1]) if len(argv) > 1 else DEFAULT_PROFILE
    result = extract(pdf, mode="records", profile_file=profile)
    rows = [record for rs in result.record_sets for record in rs.records]
    print(
        f"{len(rows)} transactions on {len(result.record_sets)} pages; issues: "
        f"{sorted({i.code for i in result.issues if i.severity != 'info'}) or 'none'}"
    )

    print(f"\n{'date':<11}{'description':<32}{'branch':<9}{'amount':>16}{'balance':>16}")
    for r in rows:
        print(
            f"{r['date'].normalized or r['date'].raw:<11}{r['description'].raw[:31]:<32}"
            f"{r['branch'].raw[:8]:<9}{r['amount'].normalized:>16}{r['balance'].normalized:>16}"
        )

    text = "\n".join(page.text for page in result.pages)
    opening = summary_value(text, "SALDO ANTERIOR")
    amounts = [Decimal(r["amount"].normalized) for r in rows]
    checks = {
        "every date has a year inside the period": all(r["date"].normalized for r in rows),
        "SALDO ANTERIOR + VALOR = SALDO (every row)": all(
            opening + sum(amounts[: i + 1]) == Decimal(r["balance"].normalized)
            for i, r in enumerate(rows)
        ),
        "credits = TOTAL ABONOS": sum(a for a in amounts if a > 0)
        == summary_value(text, "TOTAL ABONOS"),
        "debits = TOTAL CARGOS": -sum(a for a in amounts if a < 0)
        == summary_value(text, "TOTAL CARGOS"),
        "SALDO ANTERIOR + all VALOR = SALDO ACTUAL": opening + sum(amounts)
        == summary_value(text, "SALDO ACTUAL"),
    }
    print()
    for name, ok in checks.items():
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
