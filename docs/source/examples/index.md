# Examples

Self-contained, runnable examples, each built around one real task. The sources live in
the repository's `examples/` folder: every example has its input `data/`, any profile it
needs, its scripts and the expected output in `results/`. `tests/test_examples.py` runs
every documented command and compares the output, so these pages stay correct.

All documents are fictional. Run every command from the repository root.

| # | Example | Shows |
|---|---|---|
| 01 | {doc}`01_quickstart` | smallest input for text, PDF table → records, CSV → records |
| 02 | {doc}`02_research_note` | text and a results table from a scientific-style report |
| 03 | {doc}`03_bank_statement_pdf` | multi-page statement → normalized records; reconcile balances |
| 04 | {doc}`04_bank_csv_export` | `;` delimiter, cp1252 encoding, German headers → records |
| 05 | {doc}`05_parquet_and_duckdb` | export records to Parquet and analyse with SQL |
| 06 | {doc}`06_borderless_invoice` | tables without cell borders: guessing fails, `pdf.table_from_header` works |
| 07 | {doc}`07_compare_with_source` | page image next to extracted tables, for your own files |
| 08 | {doc}`08_statement_without_lines` | header-based table, `DD/MM` dates with the year from the statement period |

To regenerate the demo data or refresh expected results after an intended change:

```sh
python examples/make_demo_data.py            # every examples/*/data/ file (needs reportlab)
python examples/make_demo_data.py --results  # also every examples/*/results/ file
```

```{toctree}
:hidden:

01_quickstart
02_research_note
03_bank_statement_pdf
04_bank_csv_export
05_parquet_and_duckdb
06_borderless_invoice
07_compare_with_source
08_statement_without_lines
```
