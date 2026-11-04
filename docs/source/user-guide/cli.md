# Command-line interface

There are three commands. `doc-extractor --help` lists all of them with all of their
flags; `doc-extractor <command> --help` explains each flag. The full help text is
reproduced in {doc}`../reference/cli`.

## `inspect`

```sh
doc-extractor inspect PATH
```

Prints file name, format, size, SHA-256 and the PDF page count (or the guessed CSV
delimiter). It extracts and prints no content and has no other options. Use it to check
a file is readable and to note its hash.

## `extract`

```sh
doc-extractor extract PATH [--mode M] [--to F] [--output PATH] [how] [CSV options] [limits]
```

### What and where

| Flag | Values | Default | Meaning |
|---|---|---|---|
| `--mode` | `all` `content` `tables` `records` | `all` | what to extract ({ref}`modes <concepts-mode>`) |
| `--to` | `json` `markdown` `text` `parquet` `arrow` | `json` | output format ({ref}`formats <concepts-output>`) |
| `--output PATH` | new file, or new directory for parquet/arrow | stdout | where to write |

### How (choose at most one)

| Flag | Meaning |
|---|---|
| `--preset ID` | built-in generic preset |
| `--profile-file YAML` | your source profile; needed for `--mode records` |
| `--profile ID` | source profile from a trusted installed package |

### CSV options

These override auto-detection **and** values set in a profile.

| Flag | Values | Default |
|---|---|---|
| `--delimiter` | `,` `;` `tab` `\|` | detected from the first 32 KiB |
| `--encoding` | `utf-8` `utf-8-sig` `cp1252` `latin-1` | UTF-8 with or without BOM |
| `--csv-header` | `first` (first row has column names), `none` | `first` |

### Limits and review

| Flag | Default | Meaning |
|---|---|---|
| `--max-bytes N` | 67108864 (64 MiB) | refuse larger inputs |
| `--max-pages N` | 150 | refuse PDFs with more pages |
| `--max-rows N` | 200000 | refuse CSVs with more rows |
| `--strict` | off | exit `3` if any warning needs review |

### Examples

```sh
# readable text of a PDF
doc-extractor extract paper.pdf --mode content --to markdown

# tables from a PDF whose columns are only aligned text
doc-extractor extract report.pdf --mode tables --preset preset.pdf.tables.borderless.v1

# a Windows-exported CSV with ';' separators
doc-extractor extract export.csv --encoding cp1252 --delimiter ';' --to markdown

# records via a profile, saved to a file
doc-extractor extract statement.pdf --mode records --profile-file bank.yaml \
  --to json --output out/statement.json

# Parquet for Polars/DuckDB
doc-extractor extract statement.pdf --mode records --profile-file bank.yaml \
  --to parquet --output out/statement_records
```

## `profiles`

| Command | What it does |
|---|---|
| `profiles list` | IDs of built-in presets and installed source profiles |
| `profiles validate YAML` | check a profile against the schema; prints ID, version, SHA-256 |
| `profiles explain PATH --profile-file YAML` | run the profile's match checks against a file and print which pass, without document values; exit `3` if it does not match |

```sh
doc-extractor profiles explain examples/06_borderless_invoice/data/demo_invoice.pdf \
  --profile-file examples/03_bank_statement_pdf/northwind_statement_pdf.yaml
```

```json
{
  "profile": "demo.northwind.statement.pdf.v1",
  "matched": false,
  "checks": [
    {"check": "required_text:Northwind Example Bank", "matched": false},
    {"check": "required_text:Account statement", "matched": false},
    {"check": "required_headers", "matched": false}
  ]
}
```
