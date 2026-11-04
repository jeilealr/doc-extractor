# Python API

The library exposes the same functionality as the CLI. Full signatures are in
{doc}`../reference/api`.

## Extract

```python
from decimal import Decimal
from doc_extractor import extract

result = extract("statement.pdf", mode="records", profile_file="bank.yaml")

result.needs_review  # True if any warning needs a human look
[i.code for i in result.issues]  # e.g. ['PDF_TABLE_STRUCTURE_HEURISTIC']

for record_set in result.record_sets:
    for record in record_set.records:
        amount = record["amount"]  # a Value
        print(amount.raw, Decimal(amount.normalized), amount.source.page, amount.source.bbox)

result.tables[0].values()  # list of rows of raw strings
result.pages[0].text  # text of page 1
result.pages[0].blocks[0].source.bbox  # bbox of the first text line
result.to_dict()  # exactly what --to json writes
```

`extract()` accepts `mode`, `preset`, `profile`, `profile_file`, `delimiter`, `encoding`,
`csv_header` (bool) and `limits` ({class}`doc_extractor.Limits`).

## Result objects

| Object | Holds |
|---|---|
| `ExtractionResult` | `pages`, `tables`, `record_sets`, `issues`, `settings`, hashes and versions |
| `Page` | `number`, `text`, `blocks` (list of `TextBlock` with `source`) |
| `Table` | `id`, `cells` (rows of `Cell`), `source`, `values()` |
| `RecordSet` | `id`, `records` (list of `{field: Value}`), `source_table_id` |
| `Value` | `raw`, `normalized`, `normalized_type`, `source`, `normalization_requested` |
| `Location` | `page`, `row`, `column`, `line`, `end_line`, `bbox` |
| `Issue` | `code`, `message`, `severity`, `location` |

## DataFrames

With the optional extras installed. Every column is a **string**; cast deliberately:

```python
import polars as pl

frame = (
    result.record_sets[0]
    .to_polars(normalized=True)
    .with_columns(
        pl.col("booking_date").str.to_date(),
        pl.col("amount").cast(pl.Decimal(scale=2)),
    )
)

result.record_sets[0].to_polars()  # raw values
result.record_sets[0].to_polars(include_normalized=True)  # raw + <field>_normalized columns
result.tables[0].to_polars()  # also .to_arrow(), .to_pandas()
```

## Exporting

```python
from doc_extractor.exporters import export_result

text = export_result(result, "markdown")  # returns a string
export_result(result, "json", "out/result.json")  # writes a new file
export_result(result, "parquet", "out/result_parquet")  # writes a new directory
```

## Errors

All expected failures raise subclasses of `doc_extractor.errors.DocExtractError`:
`UnsupportedFileError`, `InputLimitError`, `DocumentReadError`, `ProfileError` and
`ExportError`. Messages never contain document content.

## Integrating with another application

See {doc}`../development/finances-migration` for how a consuming application (e.g.
`my_finances`) should depend on doc-extractor.
