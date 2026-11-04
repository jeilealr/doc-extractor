# doc-extractor

Extract text, tables and structured records from PDF and CSV files **locally**, without
losing track of where each value came from.

- Every value keeps its source location (PDF page and bounding box, or CSV row, column and
  line), and every result records the input file's SHA-256.
- Values stay exactly as written: `1.000,50` is never silently turned into a float and
  typos are not corrected. A profile can add a normalized value (`1000.50`, `2026-03-01`)
  *next to* the original.
- When the tool is unsure it says so (`status: needs_review` plus structured issues)
  instead of guessing.
- Offline only: no cloud APIs, no model downloads, no telemetry.

It ships as a command-line tool (`doc-extractor`) and a Python library
(`from doc_extractor import extract`).

## Install

Requires Python 3.10 or newer.

```sh
conda env create -f environment.yml
conda activate doc-extractor
pip install -e '.[all,dev,docs]'
doc-extractor --help
```

The core install (`pip install -e .`) covers JSON, Markdown and text. The extras add
Parquet/Arrow (`tabular`, `arrow`), pandas, DuckDB (`sql`), tests (`dev`) and the docs
toolchain (`docs`).

## In 30 seconds

```sh
# what is this file? (metadata only, no content)
doc-extractor inspect examples/03_bank_statement_pdf/data/demo_statement.pdf

# its tables, readable
doc-extractor extract examples/03_bank_statement_pdf/data/demo_statement.pdf --mode tables --to markdown

# named, normalized records via a profile for this layout
doc-extractor extract examples/03_bank_statement_pdf/data/demo_statement.pdf --mode records \
  --profile-file examples/03_bank_statement_pdf/northwind_statement_pdf.yaml --to json
```

```python
from decimal import Decimal
from doc_extractor import extract

result = extract("statement.pdf", mode="records", profile_file="bank.yaml")
for record in result.record_sets[0].records:
    print(record["amount"].raw, Decimal(record["amount"].normalized), record["amount"].source.page)
```

The three choices of `extract` are **what** (`--mode all|content|tables|records`), **how**
(`--preset` for generic settings, or `--profile-file` for a YAML profile describing one
specific layout) and **format** (`--to json|markdown|text|parquet|arrow`).
`doc-extractor --help` lists every command with all of its flags.

## Documentation

The full documentation is a Sphinx site built locally:

```sh
make -C docs html
open docs/_build/html/index.html
```

| Section | Contents |
|---|---|
| Getting started | installation, five-minute tour |
| User guide | concepts (mode, preset, profile, output), CLI, writing profiles, Python API, checking results on private documents, limitations |
| Examples | the runnable examples below, one page each |
| Reference | full CLI help, API reference, profile YAML schema, issue and exit codes |
| Development | tests and coverage gate, conventions, roadmap, test corpora |
| About | changelog, security, audit, license |

Sources are MyST Markdown under [`docs/source/`](docs/source/).

## Examples

Self-contained and runnable, each with its data, profile, scripts and expected results.
All documents are fictional. Details in [`examples/`](examples/).

| # | Example | Shows |
|---|---|---|
| 01 | [Quickstart](examples/01_quickstart/) | smallest input for text, PDF table → records, CSV → records |
| 02 | [Research note](examples/02_research_note/) | text and a results table from a scientific-style report |
| 03 | [Bank statement PDF](examples/03_bank_statement_pdf/) | multi-page statement → normalized records; reconcile balances |
| 04 | [Bank CSV export](examples/04_bank_csv_export/) | `;` delimiter, cp1252 encoding, German headers → records |
| 05 | [Parquet and DuckDB](examples/05_parquet_and_duckdb/) | export records to Parquet, analyse with SQL |
| 06 | [Borderless invoice](examples/06_borderless_invoice/) | tables without cell borders: guessing fails, header-based columns work |
| 07 | [Compare with source](examples/07_compare_with_source/) | page image next to extracted tables, for your own files |
| 08 | [Statement without lines](examples/08_statement_without_lines/) | header-based table, `DD/MM` dates with the year from the period |

## Status and limitations

Works well on born-digital PDFs with **ruled** tables and on CSV files. Tables **without
lines** extract cleanly when a profile names their header (`pdf.table_from_header`); the
generic borderless preset only guesses. Tables continuing across pages are not merged and
scanned pages are flagged, not OCR'd. See *User guide → Limitations* in the docs.

## Development

```sh
ruff format --check . && ruff check .                                     # format, isort, lint
python -m pytest --cov=doc_extractor --cov-branch --cov-fail-under=100   # tests, 100% coverage
make -C docs html                                                         # warnings are errors
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs the same checks plus a
package build on every push. Optional: `pre-commit install` runs format and lint before
each commit.

Private documents go in `docs/private/` (git-ignored); never copy their content into
tracked files. More in *Development → Contributing* in the docs.

## License

MIT. See [`LICENSE`](LICENSE). The PDF stack is `pdfplumber` and `pdfminer.six` (MIT); the
optional dependencies are permissively licensed.
