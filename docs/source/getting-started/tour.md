# Five-minute tour

All files here are fictional and live in the `examples/` folders. Run the commands from the
repository root.

:::{tip}
When you split a command over several lines, the `\` must be the **last character** on
the line. A space after it escapes the space instead of the line break, so the shell
splits the command in two (`zsh: command not found: --profile-file`).
:::

## 1. Look at a file without extracting anything

`inspect` prints metadata only, never content:

```sh
doc-extractor inspect examples/03_bank_statement_pdf/data/demo_statement.pdf
```

```json
{
  "source_name": "demo_statement.pdf",
  "format": "pdf",
  "size_bytes": 5366,
  "sha256": "a7a1bc37586b85f9d590f19ee6fa42c632d5e894059cb780a539c0a55e4feecf",
  "page_count": 2
}
```

## 2. Read the text of a PDF

`--mode content` returns the text line by line, per page:

```sh
doc-extractor extract examples/02_research_note/data/demo_research_note.pdf --mode content --to markdown
```

```text
## Page 1

Sorting Heuristics on Synthetic Workloads
R. Placeholder and S. Sample, Example Institute
Abstract
We compare three fictional sorting heuristics on synthetic workloads. The results
...
```

## 3. Get the tables

`--mode tables` finds tables on every page. The default strategy looks for ruled cell
borders:

```sh
doc-extractor extract examples/03_bank_statement_pdf/data/demo_statement.pdf --mode tables --to markdown
```

```text
### Extracted table: pdf_p1_t1

| Booking date | Value date | Description | Amount (EUR) | Balance (EUR) |
| --- | --- | --- | --- | --- |
| 01.03.2026 | 01.03.2026 | Rent March Standing order to Example Housing Ltd | -850,00 | 1.254,18 |
| 02.03.2026 | 02.03.2026 | Salary February Example Employer GmbH | 3.250,00 | 4.504,18 |
...
```

## 4. Turn a table into records with a profile

A *profile* says: "this is the Northwind statement layout; map these columns to these field
names and parse these dates and amounts". With `--mode records` you get named fields, each
with `raw`, `normalized` and `source`:

```sh
doc-extractor extract examples/03_bank_statement_pdf/data/demo_statement.pdf --mode records \
  --profile-file examples/03_bank_statement_pdf/northwind_statement_pdf.yaml --to json
```

```json
"records": [
  {
    "booking_date": {"raw": "01.03.2026", "normalized": "2026-03-01", "normalized_type": "date",
                     "source": {"page": 1, "row": 2, "column": 1,
                                "bbox": [56.69, 195.39, 126.69, 225.39]}},
    "description":  {"raw": "Rent March\nStanding order to Example Housing Ltd", "normalized": null},
    "amount":       {"raw": "-850,00", "normalized": "-850.00", "normalized_type": "decimal"},
    "balance":      {"raw": "1.254,18", "normalized": "1254.18", "normalized_type": "decimal"}
  }
]
```

Use `--to markdown` for the same records as a readable table.

## 5. The same for CSV

A German online-banking export (`;` separated, Windows `cp1252` encoding). Without help,
the tool refuses to guess the encoding:

```sh
doc-extractor extract examples/04_bank_csv_export/data/demo_bank_export.csv --to markdown
# doc-extractor: CSV cannot be decoded as UTF-8. Select --encoding cp1252 or latin-1 explicitly.

doc-extractor extract examples/04_bank_csv_export/data/demo_bank_export.csv --encoding cp1252 --to markdown
```

A profile pins encoding and delimiter, and maps the German headers to field names:

```sh
doc-extractor extract examples/04_bank_csv_export/data/demo_bank_export.csv --mode records \
  --profile-file examples/04_bank_csv_export/bank_export_csv.yaml --to markdown
```

## 6. Use the result in Python

```sh
python examples/03_bank_statement_pdf/reconcile.py
```

```text
records     20 transactions in 2 record sets
opening 2104.18  + transactions 1062.03  = 3166.21
closing printed on statement            = 3166.21
reconciled  yes, every row accounted for
```

This is explained step by step in {doc}`../examples/03_bank_statement_pdf`.

## Next steps

- {doc}`../user-guide/concepts` explains modes, presets, profiles and output formats.
- {doc}`../user-guide/profiles` shows how to write a profile for your own documents.
- {doc}`../user-guide/private-documents` shows how to check results on your own files.
