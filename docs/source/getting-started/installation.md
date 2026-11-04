# Installation

Requires Python 3.10 or newer.

```sh
git clone <repository-url> doc-extractor
cd doc-extractor
conda env create -f environment.yml
conda activate doc-extractor
pip install -e .                 # core: JSON, Markdown and text output
```

The conda environment already contains the optional data libraries. With plain `pip`,
install only the extras you need:

| Extra | Adds | Needed for |
|---|---|---|
| `tabular` | Polars | `--to parquet`, `Table.to_polars()` |
| `arrow` | Polars, PyArrow | `--to arrow`, `Table.to_arrow()` |
| `pandas` | pandas, Polars, PyArrow | `Table.to_pandas()` |
| `sql` | DuckDB | querying exported Parquet with SQL |
| `all` | all of the above | |
| `dev` | pytest, ruff, reportlab, … | tests, regenerating demo PDFs |
| `docs` | Sphinx, pydata theme, MyST | building this documentation |

```sh
pip install -e '.[all,dev,docs]'
```

Check that it works:

```sh
doc-extractor --version
doc-extractor --help
```

## Building this documentation

```sh
pip install -e '.[docs]'
make -C docs html
open docs/_build/html/index.html        # macOS; use xdg-open on Linux
```

`make -C docs clean` removes the build output. The CLI reference pages are regenerated
from the code on every build.
