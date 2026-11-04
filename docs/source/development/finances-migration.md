# Safe integration with my_finances (future; no changes applied)

The existing finance repository owns domain-specific processing and currently working PDF
parsers. This first release **does not yet replace** its Santander, Revolut or Bancolombia
extraction logic. Their source code was deliberately not copied into this new MIT repository.

Suggested dependency direction:

```text
doc_extractor (this MIT library: PDF/CSV physical readers, provenance, data contracts)
         ^
         |
doc_extractor_profiles_banking (separate, authorized bank-layout adapters)
         ^
         |
my_finances (finance-specific signs, categories, reconciliation, reports)
```

Recommended migration strategy:

1. Add `doc-extractor` as an installed library to a temporary `my_finances` development branch.
2. Use the generic CSV API for non-bank source reads and validate compatibility against existing
   CSV golden fixtures. Do not change sign interpretation or categorization.
3. Promote the working `examples/01_quickstart/payback_activity_csv.yaml` to a tested, separately
   installable banking-profile package when the output schema is agreed.
4. For each PDF bank source, create an authorized, trusted adapter using the generic pages,
   blocks and tables. Implement special geometric reconstruction without editing the core PDF
   reader. Santander, Revolut and Bancolombia need distinct algorithms.
5. On each representative statement, compare the old vs new **raw values and source spans**,
   counts, dates and identifiers, and require review for discrepancies. Only then switch the
   finance application to the new profile.
6. Preserve the bank parsers until parity is demonstrated and rollback remains possible.

Example generic API:

```python
from doc_extractor import extract

result = extract("/some/private/folder/transactions.csv", mode="all")
assert result.file_format == "csv"
# Optional tabular dependency:
frame = result.tables[0].to_polars()
```

If an installed source profile has been separately created:

```python
result = extract(
    "/private/statement.pdf", mode="records", profile="banking.santander.de.girokonto.pdf.v1"
)
if not result.record_sets or result.needs_review:
    raise RuntimeError("Source review required; do not import into finance ledger")
transactions = result.record_sets[0].to_polars()
```

This second example is an **integration target**, not yet a working bank PDF import.
