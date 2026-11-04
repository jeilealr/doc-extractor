# 03 · Bank statement PDF: records and reconciliation

**Use case:** import a monthly bank statement into a budgeting tool, and *prove* that no
transaction was lost or misread on the way.

## Files

| File | What it is |
|---|---|
| `data/demo_statement.pdf` | fictional two-page "Northwind Example Bank" statement: ruled table, header repeated on page 2, two-line descriptions, German numbers (`1.234,56`), opening and closing balance in the page text |
| `northwind_statement_pdf.yaml` | source profile: match rules, table settings, column mapping, date/decimal parsing |
| `reconcile.py` | Python: extract records, check opening + transactions = closing and every running balance |
| `results/tables.md`, `results/records.md` | expected CLI output |

## Run

```sh
# the raw tables (one per page)
doc-extractor extract examples/03_bank_statement_pdf/data/demo_statement.pdf --mode tables --to markdown

# named, normalized records
doc-extractor extract examples/03_bank_statement_pdf/data/demo_statement.pdf --mode records \
  --profile-file examples/03_bank_statement_pdf/northwind_statement_pdf.yaml --to markdown

# does the profile match? (no document values printed)
doc-extractor profiles explain examples/03_bank_statement_pdf/data/demo_statement.pdf \
  --profile-file examples/03_bank_statement_pdf/northwind_statement_pdf.yaml

# reconcile in Python
python examples/03_bank_statement_pdf/reconcile.py
```

`reconcile.py` prints:

```text
records     20 transactions in 2 record sets
opening 2104.18  + transactions 1062.03  = 3166.21
closing printed on statement            = 3166.21
reconciled  yes, every row accounted for
```

## What to notice

- **Two record sets:** the header repeats on page 2, so each page's table matches the
  profile on its own. `reconcile.py` simply concatenates them.
- **Multi-line cells** keep their line break in JSON (`"Rent March\nStanding order…"`).
  Markdown shows a space instead.
- **Exact arithmetic:** normalized amounts are strings (`"-850.00"`) and the script
  converts them with `Decimal`, so cents never drift as they could with `float`.
- **Two independent checks:** the totals check catches a missing row, and the running
  balance check also tells you *which* row (page, row, bbox) is wrong.
- **Profile as a guard:** try the profile on a different file (e.g. the invoice in example
  06). `profiles explain` shows which match checks fail, and no records are produced.

## Adapt it to your bank

Copy `northwind_statement_pdf.yaml`, change `required_text` to text that only appears on
your bank's statements, put your exact column headers into `required_headers` and
`column_mapping`, and adjust the date format and separators. If the generic table
detection does not give a clean table for your layout, see example 06 and the
limitations page in the docs.
