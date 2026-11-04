# Profile specification V1 (implemented subset)

This is a **small, deliberately non-Turing-complete** configuration language. YAML selects tested
Python operations; it must not contain Python import paths, Jinja templates, shell, SQL, network
fetches, plugin installation, or executable expressions. YAML is parsed with `yaml.safe_load`,
bounded to 128 KiB and a shallow acyclic data tree, and validated against an operation allowlist.

## Levels

- `--mode`: desired output (`content`, `tables`, `records`, `all`).
- `--preset`: bundled generic YAML (`preset.pdf.tables.borderless.v1`, etc.).
- `--profile-file`: user-supplied specialized YAML from any local path.
- `--profile`: explicitly selected profile from a **trusted installed Python package** with an
  entry point under `doc_extractor.profiles`. Installing an extension grants it Python privileges.

`--profile-file` and `--preset` cannot be combined in this V1; a specialized profile embeds the
chosen generic table settings. The `--profile` option reserves a scalable third-party mechanism,
but no banking plugin distribution is installed by this repository.

## Working operations

| Operation | Function | Parameters |
|---|---|---|
| `csv.collect_raw_rows` | Set CSV encoding/delimiter/header; preserve cells | `encoding`, `delimiter`, `first_row_header`, conservative preservation booleans |
| `pdf.collect_text_blocks` | Preserve page-local text lines and boxes | `preserve_raw`, `include_page_and_bbox` |
| `pdf.detect_tables` | Use pdfplumber line/text strategies | `vertical_strategy`, `horizontal_strategy`, bounded tolerances, provenance booleans |
| `pdf.table_from_header` | Locate a table by its header row; columns from header positions; continuation lines | `header`, `end_before_text`, `new_row_column`, `columns_x`, `y_tolerance` |
| `table.map_columns` | Map *exact* header labels to named output fields | `column_mapping`, `optional_parsing` |

A profile uses at most one table strategy: `pdf.detect_tables` or `pdf.table_from_header`.

Only dates and decimal numbers have optional normalization in V1. Dates with a year:
`%Y-%m-%d`, `%Y/%m/%d`, `%d/%m/%Y`, `%d.%m.%Y`. Dates without a year (`%d/%m`, `%d.%m.`,
`%d.%m`) require `year_from_period`, which reads the statement period from the words after two
labels and picks the only year placing the date inside it. Decimals accept amounts without a
leading zero (`-.02`). Every mapped value retains `raw`, `normalized`, `normalized_type`, and a
`source` row/column or PDF page/bbox. Decimal normalized output is **a string**, not a float.
A failed optional normalization retains the raw value and records a review issue.

## Matching and drift

For `kind: source`, `match.required_text` and/or `match.required_headers` must match; all listed
requirements are mandatory. An unrecognized or drifted source preserves generic output, writes
`LAYOUT_MISMATCH`, and produces **no mapped records**. Matching is evidence, not verification.
Header mapping is intentionally exact. V1 does **not** infer a table's header from a multi-level,
merged, or multi-page layout. Such layouts need later reusable operations or a trusted Python
adapter. No per-bank Python code has been copied into this new MIT-licensed repository.

`--profile-file` is the simplest path for users to add a supported source format. Example:

```sh
doc-extractor profiles validate examples/01_quickstart/payback_activity_csv.yaml
doc-extractor profiles explain data.csv --profile-file examples/01_quickstart/payback_activity_csv.yaml
doc-extractor extract data.csv --mode records --profile-file examples/01_quickstart/payback_activity_csv.yaml
```

## Versioning contract

- `profile_schema_version` is the grammar version: currently 1.
- `version` is the profile's own version; `id` is its stable name.
- Run results include the SHA-256 of the **YAML bytes**, the source SHA-256, backend version,
  result schema version, effective parse settings, and profile match checks.
- Source changes trigger a new fixture and a profile-version review; never silently pick a
  partly matching profile. Drift from a known layout yields an explicit warning.

## Not supported yet

No custom regex from YAML, multi-page table merges, automatic
profile detection, automatic OCR, headings/chapters classification, domain semantics, semantic
inference, custom Python adapters inside YAML, or remote models. Earlier *planning-only*
Santander/Revolut/Bancolombia YAML examples remain reference designs, not runnable profiles.

Future reader-independent operations can be added to the allowlist only together with parameter
validation, provenance requirements, security review, fixtures, and tests.
