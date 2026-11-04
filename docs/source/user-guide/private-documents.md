# Checking results on your own documents

Put private files in `docs/private/`, `private/` or `.private/`. All three are listed in
`.gitignore` and excluded from this documentation build, so nothing there is committed or
published.

## Side-by-side report

```sh
python examples/07_compare_with_source/compare_with_source.py docs/private/my_statement.pdf
open docs/private/output/my_statement/report.html
```

The report shows every page as an image, with the table regions found by each preset
outlined in colour, next to the extracted text and tables. You can see at a glance
whether a table came out the way the PDF shows it.

| Option | Meaning |
|---|---|
| `--preset ID` | preset to compare; repeatable. Default: ruled and borderless |
| `--profile-file YAML` | also run your profile and show its normalized records |
| `--output DIR` | report folder. Default: `docs/private/output/<pdf name>/` |
| `--max-pages N` | pages to render. Default: 20 |
| `--ruler PT` | draw an x-position ruler every PT points (labels every 2×PT); 0 = off. Default: 25 |
| `--anchor TEXT` | list every word's x-positions on lines containing TEXT, e.g. a header word; repeatable |
| `--force` | overwrite an existing report |

:::{warning}
The report embeds page images and extracted values. Keep it as private as the PDF.
:::

## What to compare

- **Row count:** does every transaction / line item appear exactly once?
- **Cell boundaries:** are words split across columns, or columns merged?
- **Multi-line cells:** are continuation lines kept in the right cell?
- **Numbers:** sums and running balances. A reconciliation like
  {doc}`../examples/03_bank_statement_pdf` catches missing or misread rows automatically.
- **Headers:** is the first row of each table the real header? Profiles match on it.
