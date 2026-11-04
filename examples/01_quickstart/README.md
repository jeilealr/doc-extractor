# 01 · Quickstart

The smallest possible input for each feature: text from a PDF, a ruled PDF table mapped
to records, and a CSV mapped to records. Start here if you have never run doc-extractor.

## Files

| File | What it is |
|---|---|
| `data/demo_narrative.pdf` | two pages of text with *deliberate* typos (`Tpyo`, `speling`) |
| `data/demo_ruled.pdf` | one ruled table: Date, Description, Amount |
| `data/demo.csv` | three-column Payback-style CSV (`Datum,Beschreibung,Betrag`) |
| `ruled_table_demo_pdf.yaml` | profile mapping the PDF table to `date_raw`, `description_raw`, `amount_raw` |
| `payback_activity_csv.yaml` | profile mapping the CSV, with `DD/MM/YYYY` dates and `1.000,50` amounts |
| `results/` | expected output of the commands below |

## Run

From the repository root:

```sh
# 1. text of a PDF: typos and "1.000,00" are kept exactly as written
doc-extractor extract examples/01_quickstart/data/demo_narrative.pdf --mode content --to markdown

# 2. a PDF table turned into records
doc-extractor extract examples/01_quickstart/data/demo_ruled.pdf --mode records \
  --profile-file examples/01_quickstart/ruled_table_demo_pdf.yaml --to markdown

# 3. a CSV turned into records; use --to json to see raw, normalized and source per value
doc-extractor extract examples/01_quickstart/data/demo.csv --mode records \
  --profile-file examples/01_quickstart/payback_activity_csv.yaml --to markdown
```

Expected output: `results/narrative_content.md`, `results/ruled_records.md`,
`results/csv_records.md`.

## What to notice

- The extractor never "fixes" text: `Tpyo` stays `Tpyo`.
- Run command 3 with `--to json`: `"raw": "1.000,50"` sits next to
  `"normalized": "1000.50"`, and `source` gives row, column and line in the CSV.
- Run command 3 without `--profile-file`: it exits with code `3` and the issue
  `PROFILE_REQUIRED`, because records need a profile.
