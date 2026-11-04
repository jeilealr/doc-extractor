# Concepts

`doc-extractor extract` makes three independent choices:

| Choice | Flag | Question it answers |
|---|---|---|
| mode | `--mode` | **what** to extract: text, tables or records |
| preset or profile | `--preset` / `--profile-file` / `--profile` | **how** to extract it |
| output format | `--to` | **in which format** to write it |

(concepts-mode)=
## Mode: what to extract

| `--mode` | PDF | CSV | Typical use |
|---|---|---|---|
| `all` (default) | text lines **and** tables | the file as one table | first look, debugging |
| `content` | text lines per page, no tables | not allowed (error) | papers, letters, books |
| `tables` | tables per page, no text | the file as one table | reports, statements |
| `records` | named fields mapped from tables by a **source profile** | same | importing into another app |

A table gives you anonymous rows and columns. **Records** give you named fields
(`booking_date`, `amount`, …) with normalized values next to the originals, which is
what a downstream application needs. `records` is the only mode that needs a profile;
without one, or when the profile does not match the file, it prints diagnostic output and
exits with code `3`.

## Preset vs. profile: how to extract

Choose at most one. Without any, PDF tables are detected with the ruled-lines strategy and
CSV settings are auto-detected.

`--preset ID`
: **Generic**, built-in settings for a *kind* of document, e.g. ruled vs. borderless tables.
  Presets never produce records.

`--profile-file PATH`
: **Source-specific** YAML you write for *one* layout (one bank's statement, one export
  format). It declares how to recognise the layout, which table settings to use and how
  to map columns to fields. Required for `--mode records`. See {doc}`profiles`.

`--profile ID`
: A source profile from a trusted, installed Python package (entry point group
  `doc_extractor.profiles`). None are bundled. Installing such a package grants it
  Python privileges, so install only packages you trust.

### Built-in presets

List them with `doc-extractor profiles list`.

| Preset | Format | Purpose |
|---|---|---|
| `preset.pdf.text.v1` | PDF | text lines with page and bbox |
| `preset.pdf.tables.ruled.v1` | PDF | tables with visible cell borders (same as the default) |
| `preset.pdf.tables.borderless.v1` | PDF | tables made only of aligned text; see {doc}`limitations` |
| `preset.csv.generic.v1` | CSV | generic CSV, first row as header |
| `preset.document.scientific.basic.v1` | PDF | text lines; no section/figure reconstruction yet |
| `preset.document.novel.basic.v1` | PDF | text lines; no chapter reconstruction yet |

(concepts-output)=
## Output format: `--to`

| `--to` | What you get | When to use it |
|---|---|---|
| `json` (default) | everything: text blocks, cells, records, issues, settings, hashes, provenance | further processing; the source of truth |
| `markdown` | readable pages, tables and records (no coordinates) | checking results by eye |
| `text` | plain PDF page text | papers and letters; PDF with `--mode content` or `all` only |
| `parquet` | one `.parquet` file per table or record set, plus `manifest.json` | Polars, DuckDB, pandas, large data |
| `arrow` | one Arrow IPC file per table or record set, plus `manifest.json` | Arrow-based tools |

`parquet` and `arrow` need `--output DIR` (a new directory) and the `tabular` / `arrow`
extras. Without `--output`, `json`, `markdown` and `text` print to stdout. Existing output
files and directories are **never overwritten**.

### Which combinations work

| `--mode` | json | markdown | text | parquet / arrow |
|---|---|---|---|---|
| `all` | ✅ | ✅ | ✅ PDF only | ✅ tables |
| `content` (PDF only) | ✅ | ✅ | ✅ | ✗ nothing tabular to write |
| `tables` | ✅ | ✅ | ✗ | ✅ tables |
| `records` with matching profile | ✅ | ✅ | ✗ | ✅ record sets |
| `records` without profile / no match | exit 3 + diagnostics | exit 3 | ✗ | exit 3 |

✗ means the tool refuses with exit code `2` and a message naming the alternative. In
Parquet/Arrow record exports every field keeps its raw column and fields with
normalization get an extra `<field>_normalized` column.

## Raw and normalized values

Tables always contain the exact source strings. Records carry, per field:

`raw`
: the exact cell text, e.g. `"1.254,18"`

`normalized`
: only if the profile requested parsing: `"1254.18"`, `"2026-03-01"`. Decimals are
  **strings**, so no precision is lost.

`normalized_type`
: `date` or `decimal`

`source`
: page / row / column / bbox for PDF, row / column / line for CSV

If a value cannot be parsed, `normalized` stays `null`, the raw value is kept and a
`NORMALIZATION_FAILED` issue points at the cell. To compute with amounts, convert
explicitly: `Decimal(value.normalized)` or Polars `cast(pl.Decimal(scale=2))`.

## Provenance and review

Every result contains the input's basename, size and SHA-256, the reader and pdfplumber
versions, the profile ID / version / SHA-256 and the effective settings. `status` is
`needs_review` when any issue has severity `warning` or `error`. See
{doc}`../reference/issues` for all issue and exit codes.
