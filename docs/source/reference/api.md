# Python API reference

Everything listed here is importable from the top-level package
(`from doc_extractor import extract, Limits, ...`), except the exporter and error classes,
which live in `doc_extractor.exporters` and `doc_extractor.errors`.
For a guided introduction, see {doc}`../user-guide/python-api`.

## Functions

```{eval-rst}
.. autofunction:: doc_extractor.extract

.. autofunction:: doc_extractor.inspect_file

.. autofunction:: doc_extractor.exporters.export_result
```

## Result types

```{eval-rst}
.. autoclass:: doc_extractor.ExtractionResult
   :members: needs_review, to_dict

.. autoclass:: doc_extractor.Page

.. autoclass:: doc_extractor.TextBlock

.. autoclass:: doc_extractor.Table
   :members: row_count, column_count, rectangular, values, to_polars, to_arrow, to_pandas

.. autoclass:: doc_extractor.Cell

.. autoclass:: doc_extractor.RecordSet
   :members: to_polars

.. autoclass:: doc_extractor.Value

.. autoclass:: doc_extractor.Location

.. autoclass:: doc_extractor.Issue
```

## Limits

```{eval-rst}
.. autoclass:: doc_extractor.Limits
```

## Errors

```{eval-rst}
.. automodule:: doc_extractor.errors
   :members:
   :show-inheritance:
```
