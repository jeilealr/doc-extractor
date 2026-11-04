"""Use doc-extractor from Python: extract records, do exact arithmetic, check the result.

Real use case: before importing a bank statement into a budgeting tool, confirm that
nothing was lost. The opening balance plus every transaction must equal the closing
balance printed on the statement. If one row was missed or misread, the check fails.

Run from the repository root::

    python examples/03_bank_statement_pdf/reconcile.py

Works with the core install. If the optional ``tabular`` extra (Polars) is installed it
also shows how to get a typed DataFrame.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from doc_extractor import extract

HERE = Path(__file__).resolve().parent
STATEMENT = HERE / "data" / "demo_statement.pdf"
PROFILE = HERE / "northwind_statement_pdf.yaml"


def german_amount(text: str) -> Decimal:
    return Decimal(text.replace(".", "").replace(",", "."))


def main() -> int:
    result = extract(STATEMENT, mode="records", profile_file=PROFILE)
    print(f"source      {result.source_name}  sha256={result.sha256[:12]}...")
    print(f"profile     {result.profile_id} v{result.profile_version}")
    status = "needs_review" if result.needs_review else "ok"
    print(f"status      {status}  issues={[i.code for i in result.issues]}")

    # 1. Records: one record set per matched table (here: one per page).
    rows = [record for rs in result.record_sets for record in rs.records]
    print(f"records     {len(rows)} transactions in {len(result.record_sets)} record sets")

    first = rows[0]["amount"]
    print("\nEach field keeps the source text, a normalized string and its location:")
    print(
        f"  raw={first.raw!r} normalized={first.normalized!r} "
        f"type={first.normalized_type} page={first.source.page} bbox={first.source.bbox}"
    )

    # 2. Numbers: normalized decimals are strings on purpose ("-850.00"), so converting
    #    is an explicit choice. Decimal keeps cents exact; float would not.
    total = sum((Decimal(r["amount"].normalized) for r in rows), Decimal("0"))

    # 3. Cross-check with values printed in the page text (not part of the table).
    text = "\n".join(page.text for page in result.pages)
    opening = german_amount(re.search(r"Opening balance on [\d.]+: ([\d.,-]+) EUR", text)[1])
    closing = german_amount(re.search(r"Closing balance on [\d.]+: ([\d.,-]+) EUR", text)[1])
    print(f"\nopening {opening}  + transactions {total}  = {opening + total}")
    print(f"closing printed on statement            = {closing}")

    # The balance column gives a second, row-by-row check.
    running = opening
    for record in rows:
        running += Decimal(record["amount"].normalized)
        if running != Decimal(record["balance"].normalized):
            loc = record["balance"].source
            print(
                f"MISMATCH at page {loc.page}, row {loc.row}: {running} != {record['balance'].raw}"
            )
            return 1
    ok = opening + total == closing
    print("reconciled  " + ("yes, every row accounted for" if ok else "NO, review the source"))

    # 4. Optional: a DataFrame. Every column is a string; cast deliberately.
    try:
        import polars as pl
    except ImportError:
        print("\n(polars not installed; skip DataFrame step: pip install 'doc-extractor[tabular]')")
        return 0 if ok else 1
    frame = pl.concat(rs.to_polars(normalized=True) for rs in result.record_sets).with_columns(
        pl.col("booking_date", "value_date").str.to_date(),
        pl.col("amount", "balance").cast(pl.Decimal(scale=2)),
    )
    print("\nPolars DataFrame with explicit types:")
    print(frame.head(5))
    spending = frame.filter(pl.col("amount") < 0)["amount"].sum()
    print(f"total spending: {spending}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
