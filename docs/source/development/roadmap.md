# Roadmap and acceptance criteria

## What V0.1 actually delivers

- Installable Python library/CLI with generic PDF text and basic table extraction and CSV reading.
- Source SHA-256 from the exact in-memory byte snapshot used by the reader.
- Source page/line/row/column and, where the backend supports it, PDF bounding boxes.
- Built-in generic YAML presets, safe schema validation, a source-specific CSV example,
  and a working synthetic PDF profile example.
- JSON, Markdown and text; optional Polars and Parquet/Arrow paths.
- Diagnostic warnings instead of pretending all PDF layouts are understood.
- Tests with public-distributable synthetic fixtures and a separate local private bank corpus.

## Next milestones (not yet implemented)

### V0.2 - More structure and privacy tooling

- Explicit table/cell confidence flags based on deterministic structural evidence.
- Multi-page table continuation, headers spanning rows, and candidate heading reconstruction.
- Portable CLI report of extraction completeness/source references without raw private content.
- A local review viewer highlighting original page regions; no remote upload.
- Benchmark additional freely available public PDFs downloaded by the user.
- Actual runtime verification of optional Polars/Arrow/DuckDB extras across macOS, Linux, CI.

### V0.3 - Profiles and finance bridge

- ~~Header-located tables with column boundaries and continuation lines~~: **done** as
  `pdf.table_from_header` (plus `columns_x` for explicit boundaries), and day-month dates with
  the year from the statement period (`year_from_period`). Verified on the fictional
  examples 06 and 08 and on a private Bancolombia statement (all balances reconcile).
- Profiles for Revolut (borderless, multi-line rows) and Santander (several lines per
  transaction in one ruled cell) using `pdf.table_from_header`, kept outside this repository.
- Reusable row-grouping and text-line pattern operations with bounded expressions.
- Santander and Revolut adapters and conservative layout fingerprints, including drift fixtures.
- Bancolombia and other documents only after independent ground truth and appropriate licensing.
- Package bank adapters separately and compare outputs with current working finance scripts.

### V0.4 and later

- OCR for scanned PDFs with permissively licensed tools/models (after license audit).
- Complex scientific layouts, reading-order reconstruction, equation/figure relations.
- Safe sandbox and per-job CPU/memory/time limits for untrusted user uploads.
- Optional structured document search and report generation; no mandatory model APIs.

## Quality gate for every new profile

1. Detect its intended layout and reject changed/unrecognized versions.
2. Preserve original values and record source spans/coordinates.
3. Compare expected field/cell values against the visually rendered source, not guesses.
4. Include at least one positive, one negative, one layout-change regression fixture.
5. Run quick synthetic tests and real private samples without disclosing their contents.
6. Report false positives, missed values, runtime, memory and unresolved ambiguity.
