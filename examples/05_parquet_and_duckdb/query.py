"""Export statement records to Parquet, then analyse them with DuckDB SQL.

Real use case: keep extracted data in an analysis-friendly format, and answer questions
like "how much did I spend per category?" without re-reading the PDF.

    python examples/05_parquet_and_duckdb/query.py              # writes into a temp folder
    python examples/05_parquet_and_duckdb/query.py out/parquet  # or a new folder of your choice

Needs the optional extras: pip install 'doc-extractor[tabular,sql]'
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import duckdb

from doc_extractor import extract
from doc_extractor.exporters import export_result

EXAMPLES = Path(__file__).resolve().parents[1]
STATEMENT = EXAMPLES / "03_bank_statement_pdf" / "data" / "demo_statement.pdf"
PROFILE = EXAMPLES / "03_bank_statement_pdf" / "northwind_statement_pdf.yaml"


def main(argv: list[str]) -> int:
    target = Path(argv[0]) if argv else Path(tempfile.mkdtemp()) / "statement_records"

    # Same as: doc-extractor extract ... --mode records --profile-file ... --to parquet --output DIR
    result = extract(STATEMENT, mode="records", profile_file=PROFILE)
    export_result(result, "parquet", target)
    print(f"exported {sorted(p.name for p in target.iterdir())} to {target}")

    # One parquet file per record set (here: per page). Every field has its raw column and,
    # where the profile normalizes it, a <field>_normalized column. All columns are strings,
    # so the SQL casts explicitly.
    con = duckdb.connect()
    con.read_parquet(str(target / "records_*.parquet")).create_view("records")
    con.sql("""
        CREATE VIEW transactions AS
        SELECT CAST(booking_date_normalized AS DATE)      AS day,
               split_part(description, chr(10), 1)        AS category,
               CAST(amount_normalized AS DECIMAL(12, 2))  AS amount
        FROM records
    """)
    print("\nspending by category:")
    con.sql("""
        SELECT category, count(*) AS n, sum(amount) AS total
        FROM transactions WHERE amount < 0
        GROUP BY category ORDER BY total
    """).show()

    print("income vs spending:")
    con.sql("""
        SELECT sum(amount) FILTER (WHERE amount > 0) AS income,
               sum(amount) FILTER (WHERE amount < 0) AS spending,
               sum(amount)                           AS net
        FROM transactions
    """).show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
