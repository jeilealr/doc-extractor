# Bank profile design sketches (not runnable)

These YAML files describe what the Santander, Revolut and Bancolombia statement layouts
would need. They are **design notes, not profiles**: they use operations that do not exist
yet, so loading one fails with a clear "design-only profile sketch" error instead of
mis-reading bank data. CI checks that they keep failing.

| Sketch | Layout problem (found on private statements, 2026-11-04) | Status |
|---|---|---|
| `bancolombia_statement_pdf.yaml` | no drawn lines (background image), `DD/MM` dates | **solvable now** with `pdf.table_from_header` + `year_from_period`; verified on a private statement, see `examples/08_statement_without_lines` for the fictional equivalent |
| `revolut_statement_pdf.yaml` | borderless: horizontal rules only, multi-line descriptions | to do: `pdf.table_from_header` with `new_row_column` |
| `santander_statement_pdf.yaml` | ruled grid, but each transaction spans several text lines inside one large cell; `DD.MM.` dates | to do: `pdf.table_from_header` with `new_row_column`, `%d.%m.` + `year_from_period` |

The sketches themselves still describe the earlier plan (Python adapters, regex rows) and stay
non-runnable. Working profiles replace them, one by one, in a git-ignored folder.

## From sketch to working profile

1. Start from the closest fictional example (`examples/08_statement_without_lines`).
2. Write the real profile in a git-ignored folder (e.g. `private/profiles/bancolombia.yaml`).
   It is tuned on private statements, so it does not belong in this public repository or in
   `src/`.
3. Check it with `doc-extractor profiles validate`, `profiles explain`, and the comparison
   report (`examples/07_compare_with_source`), then reconcile balances as in
   `examples/03_bank_statement_pdf/reconcile.py`.
4. Later, distribute verified bank profiles separately (a bank-profiles package or
   `my_finances`), never inside the core package.

No real bank statements or identifying information are stored here.
