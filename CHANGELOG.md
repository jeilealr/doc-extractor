# Changelog

## 0.1.0 (continued, branch `v0.1.0`, not yet released)

- **`pdf.table_from_header`**: new profile operation for tables without (usable) lines.
  Finds the header row by its column names, places column boundaries in the empty gaps
  between columns (or uses explicit `columns_x`), groups words into rows and appends
  continuation lines (`new_row_column`), stops at `end_before_text`. Reports
  `TABLE_WORD_CROSSES_COLUMN` and `TABLE_ROW_WITHOUT_START` instead of guessing.
- **Dates without a year** (`%d/%m`, `%d.%m.`, `%d.%m`) with `year_from_period`: the year is
  the only one placing the date inside the statement period read after two labels
  (`PERIOD_NOT_FOUND` otherwise). `%Y/%m/%d` added as a date format.
- Decimal normalization accepts amounts without a leading zero (`-.02`, `.00`).
- Examples: 06 now shows the header-based fix next to the failing borderless preset; new
  08 (fictional Spanish statement without lines, period across the year change,
  `check_statement.py` reconciling all totals). Comparison report gains `--ruler` and
  `--anchor` to read column positions.
- **CI** (`.github/workflows/ci.yml`, replaces `tests.yml`), modelled on FINAM: `check`
  (ruff format = black style, ruff isort rules, ruff lint, profile validation) gates
  `test` (Linux/macOS × Python 3.10/3.12/3.13, 100% coverage), `docs` (Sphinx, warnings
  are errors) and `build` (sdist + wheel, twine check, clean wheel install). Optional
  `.pre-commit-config.yaml`. Whole codebase formatted with `ruff format`; ruff pinned to
  `>=0.17,<0.18`.
- **Docs site** (Sphinx, pydata theme, MyST Markdown) under `docs/source/`, built locally with
  `make -C docs html`: getting started, user guide, examples, reference (CLI help and API
  generated from code), development, about. New `docs` extra. The former `docs/*.md` files
  moved into it.
- **Examples restructured** as self-contained numbered folders (`examples/01_quickstart/` …
  `07_compare_with_source/`), each with README, data, profile, scripts and expected
  `results/`; `tests/test_examples.py` runs every documented command against them.
  New realistic fictional documents: two-page bank statement, borderless invoice, research
  note, cp1252/semicolon bank CSV export; deterministic generator `examples/make_demo_data.py`.
- Parquet/Arrow record exports now include a `<field>_normalized` column next to each
  normalized raw column (`RecordSet.to_polars(include_normalized=True)`).
- CLI help explains modes, presets vs. profiles, output formats and exit codes; top-level
  `--help` lists every command's flags.
- Markdown table output includes the `| --- |` delimiter row.
- `--to text` refusal names the alternatives.
- Markdown output says when no tables were found (with the hint), instead of printing an
  empty line. Loading a design-only bank profile sketch (now in `docs/design/bank-profiles/`) now explains that it is
  design-only, instead of "Unknown keys in profile: processor".
- README shortened to an overview linking to the docs and examples.
- Test isolation fix: the pandas adapter test no longer imports real pandas against a fake
  `pyarrow` module; added coverage for tabular export without Polars.

## 0.1.0 - 2026-11-04

Standalone CLI and Python library release; updated test-complete build keeps 0.1.0.

**Post-preview update (2026-11-04):**
- Renamed package distribution and CLI from `doc-extract` to `doc-extractor`, and
  Python import from `doc_extract` to `doc_extractor` (breaking preview-name change).
- Expanded synthetic regression tests from 61 to 201, covering every executed
  source statement and branch under Python 3.13 (100% measured coverage).
- Corrected YAML alias validation so reused collection aliases are rejected as
  documented, not merely recursive self-references.
- Added explicit CI `--cov-fail-under=100` and `DOC_EXTRACTOR_REQUIRE_EXTRAS=1`
  to fail CI if real Polars/Arrow/DuckDB/Pandas integration dependencies are unavailable.
- Repeated private-corpus read smoke test (42/42 inputs, no private data bundled).
- Documented mock-vs-real integration testing and the new package/module names.

- Generic CSV and born-digital PDF readers with document/source provenance.
- Versioned YAML generic presets and working custom source-profile examples.
- Document layout fingerprints, strict operation validation and fail-closed record mapping.
- Source snapshot checksum, source-spelling fidelity, optional date/decimal normalization.
- JSON/Markdown/text, optional Polars/Parquet/Arrow and Pandas adapters.
- Private local paths, non-overwriting output, constrained input limits.
- Test suite and audit with synthetic fixtures; private bank corpus not redistributed.

Known limitations: advanced scientific layout recognition, image OCR, complex bank PDF record
adapters, dynamic multi-page table merging, runtime validation of optional binary extras.
