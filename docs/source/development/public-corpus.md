# Public document evaluation corpus (manual downloads, NOT bundled)

The included repository uses **self-authored synthetic PDFs** for reproducible offline tests.
It does not distribute proprietary or personal PDFs. To evaluate additional public document
layouts, obtain your own local copies of these candidates:

| Category | Candidate source | Why it adds value |
|---|---|---|
| Scientific article | [Attention Is All You Need (arXiv)](https://arxiv.org/pdf/1706.03762) | Multi-column text, equations, figures and complex tables |
| Statistical report | [US Bureau of Labor Statistics CPI](https://www.bls.gov/news.release/pdf/cpi.pdf) | Dense tables, grouped headers, footnotes and mixed text |
| Novel | [Pride and Prejudice, PDF edition](https://www.planetebook.com/free-ebooks/pride-and-prejudice.pdf) | Chapters, paragraphs, repeated headers, and line-wrapping |

A link being publicly accessible does not automatically grant redistribution rights to its PDF
edition. Read the applicable source and edition terms before including its binary in a repo.

**These public PDF binaries could not be downloaded in this execution environment, so they were
not benchmarked against the new CLI.** This is an open test task, not a claimed success.

After downloading each PDF into a private or disposable local directory:

```sh
doc-extractor inspect /path/to/public-paper.pdf
doc-extractor extract /path/to/public-paper.pdf --mode content --to markdown \
  --output /path/to/results/paper.md

doc-extractor extract /path/to/public-cpi.pdf --mode tables --to json \
  --output /path/to/results/cpi-tables.json

doc-extractor extract /path/to/public-paper.pdf --mode tables \
  --preset preset.pdf.tables.borderless.v1 --to json \
  --output /path/to/results/paper-borderless.json
```

Evaluate fidelity manually using the rendered PDF as the source of truth. Compare paragraph
text, lines, row and column grouping, pages, heading candidates, footnotes and table cells.
Do not infer that a result is accurate simply because the parser finished successfully.

A future gold-standard corpus should include source-relative bounding boxes and verified
character-level/field-level matches for representative pages, and should track unseen layouts.
