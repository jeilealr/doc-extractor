# What works and what does not (yet)

## Works well

- Born-digital PDFs with **ruled tables** (visible cell borders), including multi-line
  cells and tables repeated on every page (one table / record set per page).
- PDF text, line by line, with page and bounding box.
- CSV in UTF-8, UTF-8-BOM, cp1252 or latin-1, separated by `,` `;` tab or `|`, with exact
  row and line provenance.
- Exact header → field mapping with strict date and decimal normalization.

## Known limitations

Borderless tables need a profile
: The generic borderless preset infers columns from text alignment. When columns mix left-
  and right-aligned text, it cuts words in half and pulls in surrounding page text. A
  profile with `pdf.table_from_header` fixes this by taking the columns from the header row
  ({doc}`../examples/06_borderless_invoice`). Compare on the fictional invoice:

  ```sh
  doc-extractor extract examples/06_borderless_invoice/data/demo_invoice.pdf --mode tables \
    --preset preset.pdf.tables.borderless.v1 --to markdown
  ```

  ```sh
  doc-extractor extract examples/06_borderless_invoice/data/demo_invoice.pdf --mode tables \
    --profile-file examples/06_borderless_invoice/invoice_pdf.yaml --to markdown
  ```

Real bank statements need a profile each
: Statements tested privately show three failure patterns of the generic presets: several
  text lines per transaction inside one large cell; borderless layouts with only horizontal
  rules; and lines that are only a background image (no table detected). `pdf.table_from_header`
  with `new_row_column` addresses all three; a profile per layout is still needed. See the
  {doc}`bank profile notes <../development/bank-profiles>` and
  {doc}`../examples/08_statement_without_lines`.

Other limitations
: - Tables continuing across pages are not merged; multi-level or merged headers are not
    reconstructed.
  - Reading order on multi-column pages is heuristic.
  - Scanned (image-only) pages are flagged `OCR_REQUIRED`; no OCR is run.
  - The scientific and novel presets keep text lines; they do not rebuild sections,
    equations or figure references.

Profiles are evidence, not proof
: A matching profile shows that a file *looks like* the expected layout. It does not
  certify that every value is correct. Compare against the source when accuracy matters.
