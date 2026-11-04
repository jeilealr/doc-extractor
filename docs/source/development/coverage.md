# Test coverage and quality gate (v0.1.0)

## Scope of the measured result

- Local environment: Python 3.13.5, Linux, 2026-11-04.
- Measurement: `pytest-cov`/`coverage.py`, **all 958 tracked Python source statements**
  and **all 406 tracked source branches** in `src/doc_extractor`.
- Result: **201 passed, 4 skipped; 100% statement and branch coverage**.
- No source files or missing functions were omitted from the coverage configuration.
  Some defensive branches are exercised with synthetic or monkeypatched failure conditions.
- This is **code coverage**, not a correctness guarantee for arbitrary PDF or CSV inputs.
  True source-value accuracy still needs independently reviewed golden documents.

## The four skipped integration tests

The environment lacks Polars, PyArrow and DuckDB wheels and cannot download them.
The resulting skips are the four tests in `tests/test_optional_integrations.py`:
real Polars+Parquet, real Arrow IPC, DuckDB-over-Parquet, and Pandas conversion.

Separate tests use fake backend objects to exercise serialization *control flow*,
error handling, and provenance manifests. These fakes never claim to produce real
Arrow/Parquet binary files. The `DOC_EXTRACTOR_REQUIRE_EXTRAS=1` test mode imports
real packages and **fails rather than skips** if any required extra is missing.

## Commands

```sh
python -m pip install -e '.[all,dev]'
DOC_EXTRACTOR_REQUIRE_EXTRAS=1 python -m pytest -q \
  --cov=doc_extractor --cov-branch \
  --cov-report=term-missing --cov-fail-under=100
```

The CI matrix runs this same required-extras mode on Linux/macOS and Python
3.10, 3.12 and 3.13. The CI pipeline (`.github/workflows/ci.yml`) has not been run on GitHub yet; all of its
job commands were run locally on macOS with Python 3.11.

## Limits of 100% coverage

- Every measured Python branch was exercised, but this does not prove that all
  file combinations, malformed binary PDF paths, or adversarial inputs are safe.
- Source-specific Santander/Revolut/Bancolombia record extraction is still a roadmap
  item, not part of the implemented `doc_extractor` code or its coverage denominator.
- Scanned-PDF OCR and complex scientific layout reconstruction are not implemented.
- Performance checks on private documents are separate from unit-test coverage.
