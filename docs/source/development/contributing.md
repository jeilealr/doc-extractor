# Contributing and testing

## Setup

```sh
conda env create -f environment.yml
conda activate doc-extractor
pip install -e '.[all,dev,docs]'
```

## Checks

The same checks run in CI (`.github/workflows/ci.yml`), modelled on
FINAM's pipeline: **check → test / docs / build**. FINAM uses black, isort and pylint;
here [ruff](https://docs.astral.sh/ruff/) does all of it in one tool, so formatting and
import order can never disagree.

| CI job | Local command | What it checks |
|---|---|---|
| check | `ruff format --check --diff .` | black-style formatting (100 columns); fix with `ruff format .` |
| check | `ruff check --select I .` | import order (isort rules); fix with `ruff check --select I --fix .` |
| check | `ruff check .` | pyflakes, pycodestyle, bugbear, pyupgrade, bandit security rules |
| check | `doc-extractor profiles validate <yaml>` | every preset and example profile is valid; planned profiles are rejected |
| test | `DOC_EXTRACTOR_REQUIRE_EXTRAS=1 python -m pytest --cov=doc_extractor --cov-branch --cov-fail-under=100` | all tests including examples, 100% statement **and** branch coverage, real Polars/Arrow/DuckDB/pandas; Linux + macOS, Python 3.10 / 3.12 / 3.13 |
| docs | `make -C docs html` | Sphinx build, warnings are errors |
| build | `python -m build && twine check --strict dist/*` | sdist + wheel build, metadata valid, the wheel installs and ships the presets |

Ruff's rules and format settings live in `pyproject.toml` (`[tool.ruff]`). Its version is
pinned to a minor range (`ruff>=0.17,<0.18`) in the `dev` extra and in CI, because the
formatter's style can change between minor versions.

### Pre-commit hooks (optional)

Run the format and lint checks automatically on every commit:

```sh
pip install pre-commit
pre-commit install
pre-commit run --all-files    # once, on everything
```

The hooks (`.pre-commit-config.yaml`) use the ruff from your environment, plus basic
YAML/TOML, whitespace and large-file checks.

## Repository layout

| Path | Contents |
|---|---|
| `src/doc_extractor/api.py` | `extract()` and `inspect_file()` |
| `src/doc_extractor/cli.py` | the CLI; its help text is user documentation, so keep it in sync with these docs |
| `src/doc_extractor/readers/` | PDF (pdfplumber) and CSV (stdlib) readers |
| `src/doc_extractor/profiles/` | YAML loader and allowlists, matching, column mapping and normalization |
| `src/doc_extractor/exporters/` | JSON / Markdown / text / Parquet / Arrow |
| `src/doc_extractor/presets/` | bundled generic presets |
| `tests/` | tests; they build their own fixtures in `conftest.py` |
| `examples/` | runnable examples, see {doc}`../examples/index` |
| `docs/source/` | this documentation (Sphinx + MyST Markdown) |

## Conventions

- **Raw values stay raw.** Normalized decimals are strings; never parse to `float`.
- **Profiles are configuration, not code.** A new YAML key or operation must be added to
  the allowlists in `profiles/loader.py` (and `readers/pdf_reader.validate_table_settings`
  for table settings), with validation, tests and documentation.
- **Fail closed.** Unknown layouts produce `LAYOUT_MISMATCH` and no records, never a
  best guess.
- **Test fakes:** when a test puts a fake module into `sys.modules` (e.g. `pyarrow`), also
  stub every real package that would import it (e.g. `pandas`); otherwise results depend
  on test order.
- **Private documents** belong in `docs/private/`, `private/` or `.private/` (git-ignored).
  Never copy their content into tests, fixtures, examples or docs.

## Changing example output

If a change alters what an example prints, `tests/test_examples.py` fails. Refresh the
expected files and review the diff before committing:

```sh
python examples/make_demo_data.py --results
git diff examples/*/results/
```
