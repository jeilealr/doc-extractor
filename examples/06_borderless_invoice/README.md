# 06 · Borderless invoice: guessed columns vs. header-based columns

**Use case:** extract line items from an invoice whose table has no cell borders, only
aligned text and a rule under the header. This is very common. The example shows why
guessing columns fails, and how a profile fixes it with `pdf.table_from_header`.

## Files

| File | What it is |
|---|---|
| `data/demo_invoice.pdf` | fictional invoice: address block, invoice details, five line items, totals |
| `invoice_pdf.yaml` | profile that locates the table by its header row |
| `results/borderless_tables.md` | the (wrong) output of the generic borderless preset |
| `results/header_table_records.md` | the correct output of the profile |

## 1. The problem: guessed columns

```sh
# default (ruled) strategy: no table found, because there are no cell borders
doc-extractor extract examples/06_borderless_invoice/data/demo_invoice.pdf --mode tables --to markdown

# borderless strategy: finds "a table", but the wrong one
doc-extractor extract examples/06_borderless_invoice/data/demo_invoice.pdf --mode tables \
  --preset preset.pdf.tables.borderless.v1 --to markdown
```

```text
| Pos Description |  | Qty | Unit Uni | t price | Total |
| 1 Consulting, | requirements workshop | 8 | hours | 95.00 | 760.00 |
```

- **Words are cut** (`Uni | t price`, `Consulting, | requirements`): the borderless preset
  guesses column edges from where words start and end. Left-aligned text next to
  right-aligned numbers puts the edges in the wrong places.
- **Unrelated text is included:** the address block and totals are aligned too.
- **No setting fixes it:** the guessing itself is the problem.

## 2. The solution: columns from the header row

The profile tells the tool what the header says. Everything else follows from it:

```yaml
- op: pdf.table_from_header
  as: tables
  params:
    header: [Pos, Description, Qty, Unit, Unit price, Total]  # "Unit price" spans two words
    end_before_text: [Net amount]                             # the totals block ends the table
    new_row_column: Pos                                       # a line without Pos continues a row
```

```sh
doc-extractor extract examples/06_borderless_invoice/data/demo_invoice.pdf --mode records \
  --profile-file examples/06_borderless_invoice/invoice_pdf.yaml --to markdown
```

```text
| position | description | quantity | unit | unit_price | total |
| --- | --- | --- | --- | --- | --- |
| 1 | Consulting, requirements workshop | 8 | hours | 95.00 | 760.00 |
| 2 | Data pipeline implementation | 24 | hours | 95.00 | 2,280.00 |
...
```

## How it works

1. **Find the header line:** the line that contains all header names in this order.
2. **Column boundaries:** between two neighbouring header names, the boundary is placed in
   the empty vertical gap between the columns, so no word is cut. If a layout has no clean
   gap, give the boundaries yourself with `columns_x: [x1, x2, ...]` (PDF points; read them
   off the ruler in the example 07 report).
3. **Rows:** words below the header, up to `end_before_text`, are grouped into lines; each
   word goes to the column containing its centre. With `new_row_column`, a line that is
   empty in that column is appended to the row above (multi-line descriptions).
4. **No silent guessing:** a word crossing a column boundary adds
   `TABLE_WORD_CROSSES_COLUMN`, a continuation line before the first row adds
   `TABLE_ROW_WITHOUT_START`.

The result is a normal table (header row, cells with page and bbox), so matching, column
mapping, normalization and every export work exactly as for ruled tables.
