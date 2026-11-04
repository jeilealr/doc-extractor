# Writing a profile

A profile is a small YAML file describing **one** source layout. It is configuration, not
code: only allow-listed operations and parameters are accepted, and anything else is
rejected with an error. The complete schema is in {doc}`../reference/profile-spec`.

## Anatomy

```yaml
profile_schema_version: 1
id: demo.northwind.statement.pdf.v1     # stable name, recorded in every result
version: 1.0.0                          # bump when you change the profile
kind: source                            # 'source' = one specific layout, can produce records
format: pdf                             # pdf or csv
description: Fictional bank statement with a fully ruled transaction table.

match:                                  # evidence that the file has the expected layout
  required_text: [Northwind Example Bank, Account statement]      # ALL must pass
  required_headers: [Booking date, Value date, Description, Amount (EUR), Balance (EUR)]

pipeline:
  - op: pdf.collect_text_blocks         # keep text lines with page + bbox
    as: content
    params: {preserve_raw: true, include_page_and_bbox: true}
  - op: pdf.detect_tables               # pdfplumber table detection
    as: tables
    params:
      vertical_strategy: lines          # lines | lines_strict | text
      horizontal_strategy: lines
      preserve_raw_cells: true
      include_cell_bbox: true
  - op: table.map_columns               # exact header text -> output field name
    input: tables
    as: transactions
    params:
      column_mapping:
        Booking date: booking_date
        Description: description
        Amount (EUR): amount
      optional_parsing:
        booking_date: {type: date, format: '%d.%m.%Y'}
        amount: {type: decimal, decimal_separator: ',', thousands_separator: '.'}

output: {kind: records}
validation: {require_provenance: true, layout_mismatch: needs_review}
```

### `match`

`required_text`
: strings that must appear somewhere in the PDF text (case-insensitive).

`required_headers`
: header cells that must all appear in the **first row** of at least one table.

If any check fails, the result gets `LAYOUT_MISMATCH` and **no records**. This is what
stops a profile from silently mis-reading a different or changed layout.

### `pipeline` operations

| Operation | Purpose | Parameters |
|---|---|---|
| `csv.collect_raw_rows` | CSV settings | `encoding` (`utf-8`, `utf-8-sig`, `cp1252`, `latin-1`), `delimiter` (`,` `;` `\t` `\|`), `first_row_header` |
| `pdf.collect_text_blocks` | keep text lines | `preserve_raw`, `include_page_and_bbox` (must be `true`) |
| `pdf.detect_tables` | table detection | `vertical_strategy`, `horizontal_strategy`, `min_words_vertical`, `min_words_horizontal`, `snap_tolerance`, `join_tolerance`, `intersection_tolerance`, `text_x_tolerance`, `text_y_tolerance` |
| `pdf.table_from_header` | table located by its header row, for layouts without (usable) lines | `header`, `end_before_text`, `new_row_column`, `columns_x`, `y_tolerance` (see below) |
| `table.map_columns` | header → field mapping | `column_mapping`, `optional_parsing` |

Use **one** table step: `pdf.detect_tables` when cells have drawn borders,
`pdf.table_from_header` otherwise.

### `pdf.table_from_header`

```yaml
- op: pdf.table_from_header
  as: tables
  params:
    header: [FECHA, DESCRIPCIÓN, SUCURSAL, DCTO., VALOR, SALDO]  # column names, in order
    end_before_text: [FIN ESTADO DE CUENTA, "DCF:"]              # table ends above these
    new_row_column: FECHA          # a line empty in this column continues the row above
    # columns_x: [70, 255, 330, 400, 500]   # optional explicit boundaries (PDF points)
    # y_tolerance: 3                         # words this close vertically form one line
```

`header`
: the column names exactly as printed, in order; a name may span several words
  (`Unit price`). The header must be on one line. Pages without it get no table.

`end_before_text`
: the table ends above the first line containing any of these texts (footers, totals,
  closing lines). Without it, the table runs to the end of the page.

`new_row_column`
: multi-line rows: a line whose cell in this column is empty is appended to the previous
  row, joined with a line break.

`columns_x`
: by default each boundary is placed in the empty gap between two columns. Give explicit
  boundaries when a layout has no clean gap (a `TABLE_WORD_CROSSES_COLUMN` issue says so);
  read them off the ruler of the comparison report ({doc}`private-documents`).

Worked examples: {doc}`../examples/06_borderless_invoice` and
{doc}`../examples/08_statement_without_lines`.

### `optional_parsing`

| `type` | Settings | Example |
|---|---|---|
| `date` | `format`: `'%Y-%m-%d'`, `'%Y/%m/%d'`, `'%d/%m/%Y'` or `'%d.%m.%Y'` | `01.03.2026` → `2026-03-01` |
| `date` without year | `format`: `'%d/%m'`, `'%d.%m.'` or `'%d.%m'` **plus** `year_from_period: {start_label, end_label, format}` | `14/01` + `DESDE: 2025/12/31 HASTA: 2026/03/31` → `2026-01-14` |
| `decimal` | `decimal_separator`, `thousands_separator` (one character each, different) | `1.254,18` → `1254.18` |

Decimal parsing is strict: currency symbols, spaces inside numbers or wrong grouping fail
with `NORMALIZATION_FAILED` and the raw value is kept. Amounts without a leading zero
(`-.02`, `.00`) are accepted.

Year inference never guesses: no period found (`PERIOD_NOT_FOUND`), a date outside the
period, or a period longer than a year keep the raw value with `NORMALIZATION_FAILED`.

## Workflow

1. Find table settings that give a clean table:

   ```sh
   doc-extractor extract file.pdf --mode tables --to markdown
   doc-extractor extract file.pdf --mode tables --preset preset.pdf.tables.borderless.v1 --to markdown
   ```

   For a visual check, use {doc}`private-documents`.

2. Copy one of the profiles listed below and put in the **exact** header texts.
3. Validate it, then test the match:

   ```sh
   doc-extractor profiles validate my.yaml
   doc-extractor profiles explain file.pdf --profile-file my.yaml
   ```

4. Extract records:

   ```sh
   doc-extractor extract file.pdf --mode records --profile-file my.yaml --to markdown
   ```

5. Check the values against the source (reconciliation, see
   {doc}`../examples/03_bank_statement_pdf`) and bump `version` with every change.

## Multi-page tables

Every table whose first row contains all mapped headers becomes its **own** record set. A
statement that repeats its header on each page gives one record set per page; concatenate
them (`[r for rs in result.record_sets for r in rs.records]`). Tables that continue on the
next page *without* repeating the header are not merged yet.

## Bundled example profiles

| File | Source |
|---|---|
| `examples/03_bank_statement_pdf/northwind_statement_pdf.yaml` | fictional two-page ruled bank statement |
| `examples/04_bank_csv_export/bank_export_csv.yaml` | fictional German bank CSV (`;`, cp1252) |
| `examples/01_quickstart/payback_activity_csv.yaml` | three-column Payback-style CSV |
| `examples/01_quickstart/ruled_table_demo_pdf.yaml` | minimal ruled PDF table |
