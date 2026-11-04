"""Build a local HTML report that shows each PDF page next to what doc-extractor found.

Use it to judge, visually, whether tables and text were extracted the way the PDF shows
them, and to compare presets or a profile on your own documents. Everything runs locally;
the report embeds page images and extracted values, so treat it as private as the PDF.

    # public demo
    python examples/07_compare_with_source/compare_with_source.py \\
        examples/03_bank_statement_pdf/data/demo_statement.pdf

    # your own file, compare both table presets and your profile
    python examples/07_compare_with_source/compare_with_source.py docs/private/my_statement.pdf \\
        --profile-file private/profiles/my_statement.yaml

By default the report goes to ``docs/private/output/<pdf name>/report.html``, a folder that
``.gitignore`` excludes. An existing report is never overwritten unless ``--force`` is given.
Then open the report in a browser, e.g. ``open docs/private/output/<name>/report.html``.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import sys
from pathlib import Path

import pdfplumber
from PIL import ImageDraw

from doc_extractor import extract
from doc_extractor.models import ExtractionResult

REPO = Path(__file__).resolve().parents[2]
DEFAULT_PRESETS = ["preset.pdf.tables.ruled.v1", "preset.pdf.tables.borderless.v1"]
COLORS = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd"]

CSS = """
body{font:14px/1.45 system-ui,sans-serif;margin:0;padding:16px 24px;background:#f6f7f9;color:#1b1f24}
h1{font-size:20px;margin:4px 0}h2{font-size:17px;margin:28px 0 8px;border-top:1px solid #ccd;padding-top:16px}
h3{font-size:14px;margin:14px 0 6px}.meta{color:#556;font-size:12.5px}
.page{display:grid;grid-template-columns:minmax(300px,48%) 1fr;gap:18px;align-items:start}
.page img{width:100%;border:1px solid #ccd;background:#fff;position:sticky;top:8px}
.panel{background:#fff;border:1px solid #dde;border-radius:6px;padding:10px 12px;margin-bottom:10px;overflow-x:auto}
table{border-collapse:collapse;font-size:12px}td,th{border:1px solid #ccd;padding:2px 6px;vertical-align:top;white-space:pre-wrap}
tr:first-child td{background:#eef2f7;font-weight:600}.empty{color:#99a}
pre{white-space:pre-wrap;font-size:12px;margin:0}.issues code{background:#fff3cd;padding:1px 4px;border-radius:3px}
.legend span{display:inline-block;margin-right:14px}.sw{display:inline-block;width:11px;height:11px;margin-right:4px;vertical-align:-1px}
details summary{cursor:pointer;font-weight:600}
"""


def _png(page: pdfplumber.page.Page, boxes: list[tuple[tuple[float, ...], str]], ruler: int) -> str:
    image = page.to_image(resolution=110)
    for bbox, color in boxes:
        image.draw_rect(bbox, stroke=color, fill=(0, 0, 0, 0), stroke_width=3)
    if ruler:
        # Vertical x-position ruler in PDF points: read column positions off the image.
        image.draw_vlines(
            [x for x in range(0, int(page.width) + 1, ruler)],
            stroke=(255, 140, 0, 90),
            stroke_width=1,
        )
        draw = ImageDraw.Draw(image.annotated)
        scale = image.annotated.width / float(page.width)
        for x in range(0, int(page.width) + 1, ruler * 2):
            draw.text((x * scale + 2, 2), str(x), fill=(220, 90, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _table_html(values: list[list[str | None]]) -> str:
    rows = []
    for row in values:
        cells = "".join(
            f"<td>{html.escape(v)}</td>" if v else '<td class="empty">·</td>' for v in row
        )
        rows.append(f"<tr>{cells}</tr>")
    return "<table>" + "".join(rows) + "</table>"


def _run(pdf: Path, label: str, **kwargs) -> tuple[str, ExtractionResult | None, str | None]:
    try:
        return label, extract(pdf, **kwargs), None
    except Exception as exc:  # report the failure instead of aborting the whole report
        return label, None, f"{type(exc).__name__}: {exc}"


def _anchor_html(page: pdfplumber.page.Page, anchors: list[str]) -> str:
    """Word positions on every line containing an anchor text, e.g. a table header."""
    lines = page.extract_text_lines(return_chars=False)
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    parts = []
    for line in lines:
        if not any(a.casefold() in line["text"].casefold() for a in anchors):
            continue
        on_line = [w for w in words if w["top"] < line["bottom"] and w["bottom"] > line["top"]]
        rows = "".join(
            f"<tr><td>{html.escape(w['text'])}</td><td>{w['x0']:.1f}</td>"
            f"<td>{w['x1']:.1f}</td></tr>"
            for w in sorted(on_line, key=lambda w: w["x0"])
        )
        parts.append(
            f"<h3>line at y={line['top']:.1f}–{line['bottom']:.1f}: "
            f"{html.escape(line['text'][:80])}</h3>"
            f"<table><tr><td>word</td><td>x0 (left)</td><td>x1 (right)</td></tr>{rows}</table>"
        )
    return "<div class='panel'>" + "".join(parts) + "</div>" if parts else ""


def build(
    pdf: Path,
    presets: list[str],
    profile_file: Path | None,
    max_pages: int,
    ruler: int = 25,
    anchors: list[str] | None = None,
) -> str:
    runs = [_run(pdf, p, mode="all", preset=p) for p in presets]
    if profile_file:
        runs.append(
            _run(pdf, f"profile: {profile_file.name}", mode="records", profile_file=profile_file)
        )
    base = next((r for _, r, _ in runs if r), None)
    out = [
        f"<title>{html.escape(pdf.name)} - doc-extractor comparison</title><style>{CSS}</style>",
        f"<h1>{html.escape(pdf.name)}</h1>",
    ]
    if base:
        out.append(
            f'<p class="meta">sha256 {base.sha256} · {base.size_bytes} bytes · '
            f"{len(base.pages)} pages · reader {base.reader_version} · "
            f"pdfplumber {base.backend_version}</p>"
        )
    legend = "".join(
        f'<span><i class="sw" style="background:{COLORS[i % len(COLORS)]}"></i>'
        f"{html.escape(label)}</span>"
        for i, (label, _, _) in enumerate(runs)
    )
    out.append(f'<p class="legend">Table regions drawn on the page image: {legend}</p>')
    for label, result, error in runs:
        if error:
            out.append(
                f'<p class="issues"><b>{html.escape(label)}</b> failed: '
                f"<code>{html.escape(error)}</code></p>"
            )
        elif result:
            codes = sorted({i.code for i in result.issues})
            checks = result.settings.get("profile_match_checks", [])
            failed = [c["check"] for c in checks if not c["matched"]]
            note = f" · failed checks: {', '.join(failed)}" if failed else ""
            out.append(
                f'<p class="issues"><b>{html.escape(label)}</b>: '
                f"{len(result.tables)} tables, {len(result.record_sets)} record sets"
                f"{html.escape(note)} · " + " ".join(f"<code>{c}</code>" for c in codes) + "</p>"
            )

    with pdfplumber.open(pdf) as document:
        for number, page in enumerate(document.pages[:max_pages], start=1):
            boxes = []
            for i, (_, result, _) in enumerate(runs):
                for table in result.tables if result else []:
                    if table.source.page == number and table.source.bbox:
                        boxes.append((table.source.bbox, COLORS[i % len(COLORS)]))
            out.append(
                f"<h2>Page {number}</h2><div class='page'>"
                f"<img alt='page {number}' src='data:image/png;base64,{_png(page, boxes, ruler)}'>"
                "<div>"
            )
            if anchors:
                out.append(_anchor_html(page, anchors))
            if base and number <= len(base.pages):
                out.append(
                    "<details class='panel'><summary>Text lines (--mode content)</summary>"
                    f"<pre>{html.escape(base.pages[number - 1].text)}</pre></details>"
                )
            for i, (label, result, _) in enumerate(runs):
                if not result:
                    continue
                color = COLORS[i % len(COLORS)]
                tables = [t for t in result.tables if t.source.page == number]
                for table in tables:
                    out.append(
                        f"<div class='panel' style='border-left:4px solid {color}'>"
                        f"<h3>{html.escape(label)} · {table.id} · "
                        f"{table.row_count}×{table.column_count}</h3>"
                        f"{_table_html(table.values())}</div>"
                    )
                for rs in result.record_sets:
                    source = next((t for t in result.tables if t.id == rs.source_table_id), None)
                    if source is None or source.source.page != number or not rs.records:
                        continue
                    fields = list(rs.records[0])
                    values = [fields] + [
                        [
                            (r[f].normalized or r[f].raw)
                            if r[f].normalization_requested
                            else r[f].raw
                            for f in fields
                        ]
                        for r in rs.records
                    ]
                    out.append(
                        f"<div class='panel' style='border-left:4px solid {color}'>"
                        f"<h3>{html.escape(label)} · {rs.id} (normalized)</h3>"
                        f"{_table_html(values)}</div>"
                    )
                if not tables:
                    out.append(
                        f"<p class='meta' style='border-left:4px solid {color};"
                        f"padding-left:8px'>{html.escape(label)}: no table on this page</p>"
                    )
            out.append("</div></div>")
            page.flush_cache()
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pdf", type=Path, help="PDF to analyse")
    parser.add_argument(
        "--preset",
        action="append",
        metavar="ID",
        help="Table preset to compare (repeatable). Default: ruled and borderless",
    )
    parser.add_argument(
        "--profile-file",
        type=Path,
        metavar="YAML",
        help="Also run this source profile in --mode records",
    )
    parser.add_argument(
        "--output",
        type=Path,
        metavar="DIR",
        help="Report folder. Default: docs/private/output/<pdf name>/",
    )
    parser.add_argument("--max-pages", type=int, default=20, help="Pages to render. Default: 20")
    parser.add_argument(
        "--ruler",
        type=int,
        default=25,
        metavar="PT",
        help="Draw an x-position ruler every PT points (labels every 2*PT); 0 = off. Default: 25",
    )
    parser.add_argument(
        "--anchor",
        action="append",
        metavar="TEXT",
        help="List word x-positions on every line containing TEXT, e.g. a header word (repeatable)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing report")
    args = parser.parse_args(argv)

    folder = args.output or REPO / "docs" / "private" / "output" / args.pdf.stem
    target = folder / "report.html"
    if target.exists() and not args.force:
        print(f"{target} exists; pass --force or choose --output", file=sys.stderr)
        return 2
    report = build(
        args.pdf,
        args.preset or DEFAULT_PRESETS,
        args.profile_file,
        args.max_pages,
        ruler=args.ruler,
        anchors=args.anchor,
    )
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.write_text(report, encoding="utf-8")
    print(f"wrote {target}")
    print("It contains page images and extracted values: keep it as private as the source PDF.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
