# 02 · Research note: text and a results table

**Use case:** pull the running text and the results table out of a short scientific
report, for example to index it for search or to compare reported numbers across papers.

## Files

| File | What it is |
|---|---|
| `data/demo_research_note.pdf` | two pages: title, authors, abstract, numbered sections, a ruled results table, references (all invented) |
| `results/content.txt` | expected plain text |
| `results/tables.md` | expected table |

## Run

```sh
# plain text of every page, in reading order
doc-extractor extract examples/02_research_note/data/demo_research_note.pdf --mode content --to text

# only the table
doc-extractor extract examples/02_research_note/data/demo_research_note.pdf --mode tables --to markdown

# both, with page/bbox for every line and cell
doc-extractor extract examples/02_research_note/data/demo_research_note.pdf --mode all --to json
```

## What to notice

- `--to text` is the cleanest output for prose. Headings come out as ordinary lines:
  the scientific preset does not yet rebuild a section structure.
- Values such as `0,95` and `1.000` in the abstract are kept exactly as written.
- The table is found because its cells are ruled. The text of the table also appears in
  `--mode content`, because content mode returns *all* text on the page.
- Real papers are often two-column. Reading order there is heuristic; check
  `PDF_READING_ORDER_HEURISTIC` and compare with the source (example 07).
