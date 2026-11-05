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
- Header-located tables for PDFs without usable lines (`pdf.table_from_header`, with
  `columns_x`, `new_row_column`, `end_before_text`) and day-month dates with the year from
  the statement period (`year_from_period`). Verified on the fictional examples 06 and 08
  and on a private Bancolombia statement (all balances reconcile).
- CI (format, lint, tests at 100% coverage, docs, build), a local Sphinx docs site, and
  self-contained numbered examples whose documented output is tested.

## Still to do for V0.1

- **Profiles for Revolut** (borderless, multi-line rows) **and Santander** (several lines per
  transaction in one ruled cell) using `pdf.table_from_header`, kept outside this repository.
- **Markdown output per mode:** `tables` shows only tables, `records` shows only record sets
  with raw *and* normalized values, `all` shows records too when a profile is given (today
  records are built but not printed).
- **Document view for `all`:** one page in reading order, with each table placed where it
  sits on the page instead of after the full page text. Text lines inside a table's bounding
  box are left out (the table shows them), so header text, the table, and footer text
  (`Continued on next page.`, closing balance) appear in the order you read them. Uses the
  bounding boxes the tool already records for text lines and tables; JSON keeps everything
  unchanged.

## Next milestones (not yet implemented)

### V0.2 - More structure and privacy tooling

- Explicit table/cell confidence flags based on deterministic structural evidence.
- Multi-page table continuation, headers spanning rows, and candidate heading reconstruction.
- Portable CLI report of extraction completeness/source references without raw private content.
- A local review viewer highlighting original page regions; no remote upload.
- Benchmark additional freely available public PDFs downloaded by the user.
- Actual runtime verification of optional Polars/Arrow/DuckDB extras across macOS, Linux, CI.

### V0.3 - Profiles and finance bridge

- Reusable row-grouping and text-line pattern operations with bounded expressions.
- Santander and Revolut adapters and conservative layout fingerprints, including drift fixtures.
- Bancolombia and other documents only after independent ground truth and appropriate licensing.
- Package bank adapters separately and compare outputs with current working finance scripts.

### V0.4 and later

- OCR for scanned PDFs with permissively licensed tools/models (after license audit).
- Complex scientific layouts, reading-order reconstruction, equation/figure relations.
- Extend the document view: equations as their own blocks, and placeholders for images and
  figures (`[figure, page 3, bbox …]`) where they sit, so nothing on the page is silently
  dropped.
- Safe sandbox and per-job CPU/memory/time limits for untrusted user uploads.
- Optional structured document search and report generation; no mandatory model APIs.

## Quality gate for every new profile

1. Detect its intended layout and reject changed/unrecognized versions.
2. Preserve original values and record source spans/coordinates.
3. Compare expected field/cell values against the visually rendered source, not guesses.
4. Include at least one positive, one negative, one layout-change regression fixture.
5. Run quick synthetic tests and real private samples without disclosing their contents.
6. Report false positives, missed values, runtime, memory and unresolved ambiguity.
