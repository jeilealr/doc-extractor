# Audit report - doc-extractor v0.1.0

**Audit date:** 2026-11-04  
**Code state:** standalone renamed CLI; `my_finances` not modified. The package
and command are `doc-extractor`; the import is `doc_extractor`. Version remains 0.1.0.  
**Important provenance of this audit:** The environment did not expose a separate autonomous
agent-dispatch tool. Instead, the code was examined using **independent review tracks** for
correctness, architecture, security, performance, packaging and licensing, plus automated tests.
These are distinct review angles, **not a claim that separate AI agents audited the repo**.

## 1. Executive summary

- CLI and Python API execute on Python 3.13.5 in the provided Linux environment.
- **201 automated tests passed**, **4 real integration tests skipped** because
  Polars/PyArrow/DuckDB wheels could not be installed in this offline environment.
  Measured coverage: **100% source statements and 100% branches** (Python 3.13.5).
  Optional-backend control flow was also tested via explicit mocks; this does not
  verify real binary serialization or real DuckDB queries.
  Synthetic test corpus does not expose banking data.
- The full 42-file **private local acceptance corpus** was re-read after the rename without errors.
- Payback YAML mapping yielded 397 records on 12 source CSVs; no sign changes were applied.
- Source-specific Santander, Revolut and Bancolombia *record extraction* is **not implemented**.
  Physical PDF content extraction and generic table candidates do not prove bank-parity.
- Parquet/Arrow/Polars/DuckDB code paths require optional packages not available in this
  offline audit environment. The corresponding runtime integrations remain unverified.

## 2. Independent review tracks

| Track | What was checked | Evidence / result |
|---|---|---|
| Data fidelity and logic | Raw cell preservation, date/decimal parsing, source positions, mismatched layouts, no invisible normalization | Synthetic golden fixtures, seeded CSV round-trip, original-value checks, 397 CSV records |
| Architecture and extensibility | Separation of readers, profiles, operations, exporter, CLI; stable IDs; no finance-specific imports | Import graph review, wheel package layout, working YAML and Python API examples |
| Safety and privacy | `yaml.safe_load`, allowlisted operations, file/row/page limits, no overwrites, symlinks, malicious YAML, no network calls from core | Failing profile fixtures, source AST review, default local processing |
| Stability and error handling | Corrupt PDFs, wrong extensions, malformed CSVs, encoding errors, permission failures, optional extras unavailable | Automated pytest edge suites and CLI exit-code checks |
| Performance and memory | Time to process all 42 uploaded docs, memory pressure from pdfplumber caches | In-memory byte snapshot and explicit per-page cache flush; observed benchmark below |
| Distribution and licenses | Wheel builds, installed CLI entry point and YAML package data, dependency licenses | Offline `pip wheel`, venv install + CLI smoke; installed metadata/license review |

## 3. Issues found and addressed

| Priority | Finding | Treatment |
|---|---|---|
| High | A file could change between hashing and parsing | Readers now parse the same bounded in-memory bytes whose SHA-256 is recorded |
| High | Failed normalization could silently appear as raw data in `normalized=True` output | `normalization_requested` is explicit; failed conversion produces `None` plus review issue |
| High | Bad YAML could refer to text output as though it were a table | Type/alias validation restricts `table.map_columns` to prior table-producing operations |
| High | A profile could match a single overly generic anchor | Require at least two distinct fingerprint anchors for a source profile |
| Medium | Invalid YAML table strategy type could throw an unintended exception | Validate strategy type before membership checks |
| Medium | `records` Markdown or text-only table mode could silently return empty content | Explicit record Markdown, and reject text export for incompatible modes |
| Medium | Output could overwrite existing data | Exclusive file publication; refuse existing files and output directories, including symlinks |
| Medium | Permission errors on inputs or profile files could escape as tracebacks | Map expected I/O errors to sanitized public exceptions |
| Medium | Retained pdfplumber per-page caches inflate memory | Flush caches after extracting detached page data |
| Low | Generic profile in `records` mode did not indicate missing source mapping | Add `PROFILE_REQUIRED` and `NO_VALIDATED_RECORDS` diagnostics |
| Medium | Reused YAML collection aliases were accepted despite an explicit policy to reject them | Track visited collections across the full YAML tree; add regression tests for reuse and cycles |

## 4. Private corpus benchmark (no private contents included)

Source: user-provided 42-file private archive, loaded into an auto-deleted temporary directory.
Environment: Python 3.13.5 / pdfplumber 0.11.9, Linux. These are observed values, not
contractual performance or field-level accuracy claims.

| Group | Files read | PDF pages | Tables found | Mapped records |
|---|---:|---:|---:|---:|
| Santander PDF | 22 | 150 | 150 (candidate tables) | Not attempted |
| Revolut PDF | 4 | 43 | 0 (generic ruled strategy) | Not attempted |
| Bancolombia PDF | 4 | 6 | 0 (generic ruled strategy) | Not attempted |
| Payback CSV | 12 | N/A | 12 | 397 |
| **Total** | **42** | **199** | **162** | **397** |

- Updated reading smoke test: **11.01 seconds** across 42 files in one process
  after the package rename (same environment family; not a comparative performance benchmark).
- Earlier process maximum RSS: **approximately 204 MiB** (208,772 KiB) for the original
  0.1.0 benchmark; RSS was not re-measured after the rename. It includes
  Python libraries and cached parser state. It is not a per-document memory measurement.
- The PDF output is only **raw lines and heuristic table candidates**. Santander's 150 candidate
  tables cannot be equated with 150 verified transaction tables. Revolut and Bancolombia will
  need specialized layout adapters and additional fixtures.
- 397 Payback records were mapped with no reported normalization failures on the sample set.
  This checks structural handling but does not independently prove every input string visually.

## 5. Test and distribution verification

- `pytest` completed with **201 passed / 4 skipped**, **100% statement and branch coverage**
  across 958 tracked statements and 406 branch opportunities in the local Python 3.13
  environment. Tests include synthetic ruled/borderless PDFs, two-page text, CSV
  quoting/newlines, fixed-seed dialect fuzz, private-path avoidance, YAML restrictions,
  source drift, normalization, API/CLI error paths, and controlled backend failures.
- Optional Polars/Arrow/Parquet/Pandas paths were exercised using **mock backend objects**.
  Mocks are **not** a test of genuine binary formats or DuckDB integration. Four genuine
  integration tests remain skipped here; CI now *requires* them to run and enforces a 100%
  statement/branch coverage gate (`--cov-fail-under=100`). CI execution is not verified here.
- The renamed distribution is rebuilt and installed from a wheel as part of release verification.
- The installed `doc-extractor` entry point and bundled YAML resource discovery were smoke-tested.
  A GitHub Actions workflow is included for macOS/Linux and Python 3.10/3.12/3.13;
  it installs all extras and fails if the four real integration tests cannot import their dependencies.
  The workflow itself has not been executed in this environment.
- Static AST scan of 16 core Python modules found no direct eval/exec, shell, or network imports.
  This is a focused scan, not a general vulnerability or dependency CVE audit.
- Synthetic PDF pages were rendered visually; the ruled table and intentional spelling errors
  match the source as shown.

## 6. Permissive licensing check

Runtime packages installed in this environment were inspected via distribution metadata:

| Dependency | Installed version | License metadata |
|---|---|---|
| pdfplumber | 0.11.9 | MIT |
| pdfminer.six | 20251230 | MIT |
| pypdfium2 | 5.8.0 | BSD-3-Clause / Apache-2.0 and bundled dependency notices |
| Pillow | 12.3.0 | MIT-CMU |
| PyYAML | 6.0.3 | MIT |
| cryptography | 46.0.4 | Apache-2.0 OR BSD-3-Clause |
| cffi | 2.0.0 | MIT |

Optional Polars, DuckDB and PyArrow were not available to inspect in the local runtime;
Pandas was present, but requires Polars and PyArrow for this package's adapter.
Their advertised upstream licenses are permissive, but **verify the exact installed dependency
tree and notices before redistributing a commercial package**. No AGPL library is imported by
this project. Existing LGPL `my_finances` parser code has not been transplanted.

## 7. Residual risks and limitations (not closed)

1. **Untrusted PDF resources.** Input-size/page/character limits are safeguards but do not
   constitute a hardened sandbox. Crafted compressed streams may consume large resources before
   limits take effect. Do not expose the CLI as a public upload service without OS-level
   time/CPU/memory sandboxing and an updated dependency security audit.
2. **PDF table accuracy.** Text layers and borderless/merged/multi-column layouts can be wrong.
   The module does not visually verify each value or reconstruct multi-page tables.
3. **OCR.** Scanned PDFs produce an `OCR_REQUIRED` issue; no OCR is attempted in V0.1.
4. **Banking profiles.** Existing Santander, Revolut, Bancolombia source-specific algorithms
   have not been ported or verified for parity. Generic extraction is not a replacement.
5. **Optional features.** Actual Polars, PyArrow, DuckDB and Pandas runtime behavior was not
   end-to-end tested due unavailable dependencies and blocked package downloads.
6. **Public Internet PDFs.** Attempts to download public scientific/statistical/novel PDFs
   were blocked in this environment. Only locally generated synthetic and private samples were
   run. See `docs/source/development/public-corpus.md` for a suggested external corpus and evaluation commands.
7. **Automated vulnerability/lint tools.** Full Ruff/Bandit/OSV/Safety checks were unavailable
   offline. Static reviews and tests are useful but not a zero-vulnerability guarantee.
8. **Multi-agent audit.** No autonomous multi-agent review system was available. The review
   consists of separate automated checks and manual analysis by this assistant.

## 8. Next release gate

Before using this for real downstream account imports, install the optional tabular extras on
macOS, run the public corpus and profile parity checks, audit locked dependencies and test the
installed CLI on an independent machine. Introduce one bank PDF adapter at a time, preserving
its prior expected raw values and review behavior. See `docs/source/development/roadmap.md`.
