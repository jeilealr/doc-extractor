# doc-extractor

**Extract text, tables and structured records from PDF and CSV files, locally, without
losing track of where each value came from.**

- Every value keeps its source location (PDF page and bounding box, or CSV row, column and
  line), and every result records the input file's SHA-256.
- Values stay exactly as written: `1.000,50` is never silently turned into a float, and
  typos are not corrected. A profile can add a normalized value (`1000.50`, `2026-03-01`)
  *next to* the original.
- When the tool is unsure it says so (`status: needs_review` plus structured issues)
  instead of guessing.
- Offline only: no cloud APIs, no model downloads, no telemetry.

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} Getting started
:link: getting-started/index
:link-type: doc

Install it and try every feature in five minutes on the bundled demo documents.
:::

:::{grid-item-card} User guide
:link: user-guide/index
:link-type: doc

Modes, presets and profiles, output formats, the CLI, writing profiles, Python API.
:::

:::{grid-item-card} Examples
:link: examples/index
:link-type: doc

Runnable tasks: reconcile a bank statement, read a bank CSV export, query with DuckDB.
:::

:::{grid-item-card} Reference
:link: reference/index
:link-type: doc

Full CLI help, Python API, profile YAML schema, issue codes and exit codes.
:::

:::{grid-item-card} Development
:link: development/index
:link-type: doc

Tests and coverage gate, profile quality gate, roadmap, test corpora.
:::

:::{grid-item-card} About
:link: about/index
:link-type: doc

Changelog, security notes, audit, license.
:::
::::

```{toctree}
:hidden:
:maxdepth: 2

getting-started/index
user-guide/index
examples/index
reference/index
development/index
about/index
```
