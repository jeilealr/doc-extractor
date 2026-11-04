# 04 · Bank CSV export: encodings and delimiters

**Use case:** read the CSV that German online banking exports: `;` separated, Windows
`cp1252` encoding (umlauts), `DD.MM.YYYY` dates and `1.234,56` amounts, sometimes with a
`;` inside a quoted field.

## Files

| File | What it is |
|---|---|
| `data/demo_bank_export.csv` | six fictional transactions, cp1252-encoded, CRLF line ends |
| `bank_export_csv.yaml` | source profile: pins encoding and delimiter, maps German headers to English field names |
| `results/tables.md`, `results/records.md` | expected output |

## Run

```sh
# without help, the tool refuses to guess the encoding (exit code 2)
doc-extractor extract examples/04_bank_csv_export/data/demo_bank_export.csv --to markdown

# tell it the encoding; the ';' delimiter is detected
doc-extractor extract examples/04_bank_csv_export/data/demo_bank_export.csv --mode tables \
  --encoding cp1252 --to markdown

# or let the profile pin everything and map the columns
doc-extractor extract examples/04_bank_csv_export/data/demo_bank_export.csv --mode records \
  --profile-file examples/04_bank_csv_export/bank_export_csv.yaml --to markdown
```

## What to notice

- **No silent guessing:** a wrong encoding would turn `Gebühr` into `GebÃ¼hr`. The tool
  stops and names the options instead.
- **Quoted delimiters:** `"Kartenzahlung; Werkzeug"` stays one field.
- **Exact line provenance:** in `--to json`, `source.line` is the physical line in the
  file, so you can open the CSV at exactly that line.
- **Command line beats profile:** `--encoding` or `--delimiter` on the command line
  override the profile's values.
