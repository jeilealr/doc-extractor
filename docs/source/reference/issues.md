# Issue codes and exit codes

## Exit codes

| Code | Meaning |
|---|---|
| `0` | extraction finished |
| `2` | error: unreadable or unsupported input, invalid or unsafe profile, a limit exceeded, missing optional dependency, refused mode/format combination, or output already exists |
| `3` | needs review: `--mode records` produced no records (no profile or no match), `profiles explain` did not match, or `--strict` was given and warnings were found |

## Issue codes

Issues appear in the `issues` list of every result. `severity` is `info`, `warning` or
`error`; any `warning` or `error` sets `status: needs_review`.

| Code | Severity | Meaning | What to do |
|---|---|---|---|
| `PDF_READING_ORDER_HEURISTIC` | info | text order comes from the PDF text layer and was not visually verified | check multi-column pages |
| `PDF_TABLE_STRUCTURE_HEURISTIC` | info | detected tables are candidates | compare complex layouts with the source |
| `NO_TABLES_FOUND` | info | no ruled tables found | try `--preset preset.pdf.tables.borderless.v1`, or a profile with `pdf.table_from_header` |
| `OCR_REQUIRED` | warning | a page has no text layer (scanned image) | OCR the PDF first |
| `LAYOUT_MISMATCH` | warning | the profile's match checks failed; no records were mapped | `profiles explain` shows which check failed |
| `PROFILE_REQUIRED` | warning | `--mode records` without a source profile | add `--profile-file` |
| `NO_VALIDATED_RECORDS` | warning | records mode produced nothing | see the other issues |
| `NORMALIZATION_FAILED` | warning | a date or decimal could not be parsed; raw value kept | check the cell at `location` and the profile's format |
| `TABLE_WORD_CROSSES_COLUMN` | warning | a word lies across a column boundary of `pdf.table_from_header` | set `columns_x` explicitly |
| `TABLE_ROW_WITHOUT_START` | warning | a continuation line appeared before the first row and was skipped | check `end_before_text` / the header |
| `PERIOD_NOT_FOUND` | warning | `year_from_period` labels or dates not found; day-month dates keep their raw value | check the labels and the period date format |
| `INCOMPLETE_ROW` | warning | a row is missing a mapped cell | check the table at `location` |
| `CSV_DIALECT_UNCERTAIN` | warning | the CSV delimiter was guessed | pass `--delimiter` |
| `CSV_HEADER_UNCERTAIN` | warning | unclear whether the first row is a header | pass `--csv-header` |
| `CSV_RAGGED_ROWS` | warning | rows have different numbers of columns | check the source file |
| `CSV_EMPTY` | warning | the CSV has no rows | |

## Default limits

| Limit | Default | CLI flag |
|---|---|---|
| input size | 64 MiB | `--max-bytes` |
| PDF pages | 150 | `--max-pages` |
| CSV rows | 200 000 | `--max-rows` |
| tables per PDF page | 50 | API only (`Limits`) |
| characters per PDF page | 2 000 000 | API only (`Limits`) |
