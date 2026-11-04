# 08 · Statement without lines: header-based table and day/month dates

**Use case:** read a bank statement whose PDF draws no lines at all (the column lines you see
are part of a background image, or there are none), whose dates have no year (`14/01`), and
whose amounts below 1 have no leading zero (`-.02`). This is the layout of many Latin
American bank statements; the example is a fictional "Banco de Ejemplo".

## Files

| File | What it is |
|---|---|
| `data/demo_lineless_statement.pdf` | two pages, Spanish headers, period `DESDE: 2025/11/30 HASTA: 2026/01/31` across the year change, summary block, `FIN ESTADO DE CUENTA` and a footer |
| `lineless_statement_pdf.yaml` | profile: header-based table, end markers, year from the period |
| `check_statement.py` | prints the normalized transactions and checks them against the statement's own totals |
| `results/tables.md` | expected table output |

## Run

```sh
# what the generic presets see: no table (no lines), or a wrongly guessed one
doc-extractor extract examples/08_statement_without_lines/data/demo_lineless_statement.pdf \
  --mode tables --to markdown

# the table, located by its header row
doc-extractor extract examples/08_statement_without_lines/data/demo_lineless_statement.pdf \
  --mode tables --profile-file examples/08_statement_without_lines/lineless_statement_pdf.yaml \
  --to markdown

# normalized records, checked against SALDO ANTERIOR / TOTAL ABONOS / TOTAL CARGOS / SALDO ACTUAL
python examples/08_statement_without_lines/check_statement.py
```

`check_statement.py` prints:

```text
17 transactions on 2 pages; issues: none

date       description                     branch             amount         balance
2025-12-01 ABONO INTERESES AHORROS                              4.12      1500004.12
...
2025-12-09 AJUSTE INTERES AHORROS DB                           -0.02      2230004.10
...
2026-01-31 ABONO INTERESES AHORROS                              2.95      1655936.92

ok   every date has a year inside the period
ok   SALDO ANTERIOR + VALOR = SALDO (every row)
ok   credits = TOTAL ABONOS
ok   debits = TOTAL CARGOS
ok   SALDO ANTERIOR + all VALOR = SALDO ACTUAL
```

## The profile, part by part

```yaml
- op: pdf.table_from_header
  params:
    header: [FECHA, DESCRIPCIÓN, SUCURSAL, DCTO., VALOR, SALDO]
    end_before_text: [FIN ESTADO DE CUENTA, "DCF:"]
    new_row_column: FECHA
```

- **`header`:** found on every page; page 2 repeats it, so each page gives one table.
- **`end_before_text`:** the table ends above the footer (`DCF:` on every page) and above
  `FIN ESTADO DE CUENTA` on the last page. Without the second marker, that line has no date
  and would be appended to the last transaction's description; that is what
  `new_row_column` is for, so the end marker must stop it first.
- **`new_row_column: FECHA`:** a line without a date would continue the previous row.
- **SUCURSAL** is a separate column: its position tells it apart from the description,
  even though both are text.

```yaml
date:
  type: date
  format: '%d/%m'
  year_from_period: {start_label: 'DESDE:', end_label: 'HASTA:', format: '%Y/%m/%d'}
```

- The period is read from the words right after `DESDE:` and `HASTA:` in the page text.
- Each `DD/MM` date gets the **only** year that puts it inside the period: `31/12` → 
  `2025-12-31`, `14/01` → `2026-01-14`. Dates are normalized to ISO `YYYY-MM-DD`.
- No period found, a date outside the period, or a period longer than a year (two possible
  years) keeps the raw value and adds `PERIOD_NOT_FOUND` / `NORMALIZATION_FAILED`.

```yaml
amount: {type: decimal, decimal_separator: '.', thousands_separator: ','}
```

`-320,000.00` → `-320000.00`, `-.02` → `-0.02`.

## Use it on your own statement

Copy the profile to a git-ignored folder (e.g. `private/profiles/`), adapt `match`, the
header names and the end markers, then run the check script on your file:

```sh
python examples/08_statement_without_lines/check_statement.py \
  docs/private/my_statement.pdf private/profiles/my_statement.yaml
```
