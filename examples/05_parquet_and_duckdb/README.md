# 05 · Parquet and DuckDB: analyse extracted records

**Use case:** keep extracted transactions in an analysis-friendly format and answer
questions with SQL ("how much did I spend per category?") without touching the PDF again.

Needs the optional extras: `pip install 'doc-extractor[tabular,sql]'`.

## Files

| File | What it is |
|---|---|
| `query.py` | exports the statement records from example 03 to Parquet, then queries them with DuckDB |

## Run

The same export on the command line:

```sh
doc-extractor extract examples/03_bank_statement_pdf/data/demo_statement.pdf --mode records \
  --profile-file examples/03_bank_statement_pdf/northwind_statement_pdf.yaml \
  --to parquet --output out/statement_records
```

`out/statement_records/` then contains `records_1.parquet`, `records_2.parquet` (one per
page) and `manifest.json` (hashes, profile, issues: the full JSON result).

The script does the export into a temporary folder and runs two queries:

```sh
python examples/05_parquet_and_duckdb/query.py
```

```text
spending by category:
┌───────────────────┬───────┬───────────────┐
│     category      │   n   │     total     │
├───────────────────┼───────┼───────────────┤
│ Card payment      │     8 │      -1444.54 │
│ Rent March        │     1 │       -850.00 │
│ Direct debit      │     4 │       -293.84 │
...
income vs spending:
│       3780.36 │      -2718.33 │       1062.03 │
```

## What to notice

- **Both values are exported:** every field has its raw column (`amount` = `-850,00`) and,
  where the profile normalizes it, a `<field>_normalized` column (`-850.00`).
- **All columns are strings.** The SQL casts explicitly
  (`CAST(amount_normalized AS DECIMAL(12, 2))`), so a misparsed value fails loudly
  instead of becoming a wrong number.
- **Never overwritten:** running the CLI command twice fails the second time because
  `out/statement_records` exists. Choose a new folder.
- The "category" here is just the first line of the description. Real categorisation
  belongs in your application, not in the extractor.
