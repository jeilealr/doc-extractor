# 07 · Compare extraction with the source page

**Use case:** check, by eye, whether tables came out the way the PDF shows them, and
compare presets or your own profile on **your own private documents**.

## Files

| File | What it is |
|---|---|
| `compare_with_source.py` | builds a local HTML report: each page as an image with detected table regions outlined, next to the extracted text, tables and records |

## Run

```sh
# a public demo
python examples/07_compare_with_source/compare_with_source.py \
  examples/03_bank_statement_pdf/data/demo_statement.pdf \
  --profile-file examples/03_bank_statement_pdf/northwind_statement_pdf.yaml

# your own file (put it in docs/private/, which git ignores)
python examples/07_compare_with_source/compare_with_source.py docs/private/my_statement.pdf
open docs/private/output/my_statement/report.html
```

| Option | Meaning |
|---|---|
| `--preset ID` | preset to compare; repeatable. Default: ruled and borderless |
| `--profile-file YAML` | also run a profile and show its normalized records |
| `--output DIR` | report folder. Default: `docs/private/output/<pdf name>/` |
| `--max-pages N` | pages to render. Default: 20 |
| `--ruler PT` | draw an x-position ruler every PT points (labels every 2×PT); 0 = off. Default: 25 |
| `--anchor TEXT` | list every word's x-positions on lines containing TEXT, e.g. a header word; repeatable |
| `--force` | overwrite an existing report |

## Finding column positions

To write `columns_x` or check the automatic boundaries of `pdf.table_from_header`, use the
ruler and the header word positions:

```sh
python examples/07_compare_with_source/compare_with_source.py docs/private/my_statement.pdf \
  --anchor FECHA --force
```

The report then lists, for the header line, each word with its left (`x0`) and right
(`x1`) position in PDF points, and the page image shows the ruler.

## What to look for

Each preset or profile gets a colour; its table regions are outlined in that colour on
the page image and its tables have a matching left border.

- Does the outline cover exactly the table, or also headers, addresses and footers?
- Is every row there exactly once? Are words split across columns?
- Do multi-line cells stay together?

> **Warning:** the report embeds page images and extracted values. Keep it as private as
> the PDF.
