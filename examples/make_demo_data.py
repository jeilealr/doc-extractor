"""Generate the self-authored, redistributable demo data of every example folder.

Every name, IBAN, amount and address below is invented. The documents imitate common
real-world layouts so the examples exercise the same problems real files have:

- ``demo_statement.pdf``     two-page bank statement, ruled table, header repeated per page,
                             multi-line descriptions, German-style numbers (1.234,56)
- ``demo_invoice.pdf``       invoice whose line items have *no* cell borders (borderless preset)
- ``demo_research_note.pdf`` short scientific-style note: title, abstract, sections,
                             a ruled results table and references (content + tables)
- ``demo_bank_export.csv``   semicolon-delimited, cp1252-encoded online-banking CSV export
- ``demo_lineless_statement.pdf`` Spanish statement without any drawn lines: day/month dates,
                             a period across the year change, amounts like ``-.02``
- ``demo_ruled.pdf`` / ``demo_narrative.pdf`` / ``demo.csv``  the minimal quickstart files

Each file is written to the ``data/`` folder of the example that uses it. Requires
``reportlab`` (installed by the ``dev`` extra)::

    python examples/make_demo_data.py             # regenerate every examples/*/data/ file
    python examples/make_demo_data.py --results   # also refresh every examples/*/results/ file

Output is deterministic (``invariant=1``), so regenerating does not change file hashes
unless this script changes.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

WIDTH, HEIGHT = A4


def _canvas(path: Path) -> canvas.Canvas:
    pdf = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    pdf.setAuthor("doc-extractor examples")
    pdf.setTitle(path.stem)
    return pdf


def _de(amount: Decimal) -> str:
    """Format like German statements do: 1.234,56 and -45,80."""
    sign = "-" if amount < 0 else ""
    whole, frac = f"{abs(amount):.2f}".split(".")
    groups = []
    while whole:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    return f"{sign}{'.'.join(groups)},{frac}"


# --------------------------------------------------------------------------- statement

STATEMENT_ROWS = [
    # booking, value, description lines, amount
    (
        "01.03.2026",
        "01.03.2026",
        ["Rent March", "Standing order to Example Housing Ltd"],
        "-850.00",
    ),
    ("02.03.2026", "02.03.2026", ["Salary February", "Example Employer GmbH"], "3250.00"),
    ("03.03.2026", "03.03.2026", ["Card payment", "Corner Bakery"], "-4.60"),
    ("04.03.2026", "05.03.2026", ["Direct debit", "City Power & Water"], "-96.15"),
    ("05.03.2026", "05.03.2026", ["Card payment", "Green Grocer Market"], "-37.42"),
    ("07.03.2026", "07.03.2026", ["Transfer from savings"], "500.00"),
    ("08.03.2026", "08.03.2026", ["Card payment", "Bookshop on Main Street"], "-23.90"),
    ("10.03.2026", "10.03.2026", ["Direct debit", "Mobile Phone Co. contract 4471"], "-19.99"),
    ("11.03.2026", "11.03.2026", ["ATM withdrawal"], "-100.00"),
    ("12.03.2026", "12.03.2026", ["Card payment", "Railway ticket office"], "-58.20"),
    ("14.03.2026", "14.03.2026", ["Refund", "Online Shop order 99812"], "29.99"),
    ("15.03.2026", "16.03.2026", ["Direct debit", "Fitness Studio membership"], "-34.90"),
    ("18.03.2026", "18.03.2026", ["Card payment", "Pharmacy"], "-12.35"),
    ("19.03.2026", "19.03.2026", ["Transfer to", "A. Example (shared dinner)"], "-25.00"),
    ("21.03.2026", "21.03.2026", ["Card payment", "Hardware store"], "-1249.00"),
    ("22.03.2026", "22.03.2026", ["Card payment", "Cinema"], "-18.00"),
    ("24.03.2026", "24.03.2026", ["Direct debit", "Insurance quarterly premium"], "-142.80"),
    ("26.03.2026", "26.03.2026", ["Card payment", "Green Grocer Market"], "-41.07"),
    ("28.03.2026", "28.03.2026", ["Interest credit"], "0.37"),
    ("30.03.2026", "31.03.2026", ["Account fee March"], "-4.95"),
]
STATEMENT_OPENING = Decimal("2104.18")
STATEMENT_HEADERS = ("Booking date", "Value date", "Description", "Amount (EUR)", "Balance (EUR)")
STATEMENT_WIDTHS = (70, 70, 205, 75, 80)


def _statement_header(pdf: canvas.Canvas, page: int, pages: int) -> float:
    pdf.setFillColor(colors.HexColor("#123c69"))
    pdf.rect(0, HEIGHT - 28 * mm, WIDTH, 28 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(20 * mm, HEIGHT - 17 * mm, "Northwind Example Bank")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(WIDTH - 20 * mm, HEIGHT - 13 * mm, "Account statement")
    pdf.drawRightString(WIDTH - 20 * mm, HEIGHT - 19 * mm, f"Page {page} of {pages}")
    pdf.setFillColor(colors.black)
    y = HEIGHT - 40 * mm
    if page == 1:
        pdf.setFont("Helvetica", 10)
        for line in ("Alex Example", "12 Sample Street", "10115 Exampletown"):
            pdf.drawString(20 * mm, y, line)
            y -= 13
        pdf.setFont("Helvetica", 9)
        info = [
            ("IBAN", "DE00 1234 5678 0000 0000 00"),
            ("Statement no.", "003 / 2026"),
            ("Period", "01.03.2026 - 31.03.2026"),
        ]
        iy = HEIGHT - 40 * mm
        for label, value in info:
            pdf.drawString(120 * mm, iy, f"{label}:")
            pdf.drawString(145 * mm, iy, value)
            iy -= 13
        y -= 14
    return y


def _statement_table(pdf: canvas.Canvas, top: float, rows: list[tuple[str, ...]]) -> float:
    """Draw a fully ruled grid; each data row may hold multi-line descriptions."""
    x0 = 20 * mm
    y = top
    for r, row in enumerate(rows):
        lines = max(len(cell.split("\n")) for cell in row)
        height = 8 + 11 * lines
        x = x0
        pdf.setFillColor(colors.HexColor("#e8eef5") if r == 0 else colors.white)
        pdf.rect(x0, y - height, sum(STATEMENT_WIDTHS), height, stroke=0, fill=1)
        pdf.setFillColor(colors.black)
        for c, (width, value) in enumerate(zip(STATEMENT_WIDTHS, row, strict=True)):
            pdf.rect(x, y - height, width, height)
            pdf.setFont("Helvetica-Bold" if r == 0 else "Helvetica", 8.5)
            for i, part in enumerate(value.split("\n")):
                ty = y - 12 - i * 11
                if c >= 3 and r > 0:
                    pdf.drawRightString(x + width - 4, ty, part)
                else:
                    pdf.drawString(x + 4, ty, part)
            x += width
        y -= height
    return y


def make_statement(folder: Path) -> Path:
    balance = STATEMENT_OPENING
    body: list[tuple[str, ...]] = []
    for booking, value, desc, amount in STATEMENT_ROWS:
        amount_dec = Decimal(amount)
        balance += amount_dec
        body.append((booking, value, "\n".join(desc), _de(amount_dec), _de(balance)))
    split = 12
    target = folder / "demo_statement.pdf"
    pdf = _canvas(target)

    y = _statement_header(pdf, 1, 2)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(20 * mm, y, f"Opening balance on 01.03.2026: {_de(STATEMENT_OPENING)} EUR")
    y = _statement_table(pdf, y - 10, [STATEMENT_HEADERS, *body[:split]])
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(20 * mm, y - 14, "Continued on next page.")
    pdf.showPage()

    y = _statement_header(pdf, 2, 2)
    y = _statement_table(pdf, y, [STATEMENT_HEADERS, *body[split:]])
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(20 * mm, y - 20, f"Closing balance on 31.03.2026: {_de(balance)} EUR")
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(
        20 * mm, 18 * mm, "Please check this statement. Objections must be raised within six weeks."
    )
    pdf.drawString(
        20 * mm,
        14 * mm,
        "Northwind Example Bank is a fictional institution created for software tests.",
    )
    pdf.save()
    return target


# --------------------------------------------------------------------------- invoice

INVOICE_ITEMS = [
    ("1", "Consulting, requirements workshop", "8", "hours", "95.00"),
    ("2", "Data pipeline implementation", "24", "hours", "95.00"),
    ("3", "PDF extraction profile review", "6", "hours", "110.00"),
    ("4", "Hosting, March 2026", "1", "month", "49.00"),
    ("5", "Training session (remote)", "2", "hours", "120.00"),
]


def make_invoice(folder: Path) -> Path:
    target = folder / "demo_invoice.pdf"
    pdf = _canvas(target)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(20 * mm, HEIGHT - 30 * mm, "INVOICE")
    pdf.setFont("Helvetica", 9.5)
    left = ["Sample Studio Ltd", "4 Placeholder Lane", "20095 Demoburg"]
    right = [
        ("Invoice no.", "INV-2026-0042"),
        ("Date", "31.03.2026"),
        ("Customer no.", "C-1007"),
        ("Due", "14.04.2026"),
    ]
    for i, line in enumerate(left):
        pdf.drawString(20 * mm, HEIGHT - 45 * mm - i * 13, line)
    for i, (label, value) in enumerate(right):
        pdf.drawString(125 * mm, HEIGHT - 45 * mm - i * 13, label)
        pdf.drawRightString(WIDTH - 20 * mm, HEIGHT - 45 * mm - i * 13, value)

    # Borderless line-item table: aligned text columns, only a rule under the header.
    columns = [
        (20 * mm, "Pos", "l"),
        (35 * mm, "Description", "l"),
        (120 * mm, "Qty", "r"),
        (135 * mm, "Unit", "l"),
        (162 * mm, "Unit price", "r"),
        (WIDTH - 20 * mm, "Total", "r"),
    ]
    y = HEIGHT - 110 * mm
    pdf.setFont("Helvetica-Bold", 9.5)
    for x, label, align in columns:
        (pdf.drawRightString if align == "r" else pdf.drawString)(x, y, label)
    pdf.setLineWidth(0.6)
    pdf.line(20 * mm, y - 5, WIDTH - 20 * mm, y - 5)
    pdf.setFont("Helvetica", 9.5)
    net = Decimal("0")
    for pos, desc, qty, unit, price in INVOICE_ITEMS:
        y -= 18
        total = Decimal(qty) * Decimal(price)
        net += total
        values = [pos, desc, qty, unit, f"{Decimal(price):,.2f}", f"{total:,.2f}"]
        for (x, _, align), value in zip(columns, values, strict=True):
            (pdf.drawRightString if align == "r" else pdf.drawString)(x, y, value)
    pdf.line(120 * mm, y - 8, WIDTH - 20 * mm, y - 8)
    vat = (net * Decimal("0.19")).quantize(Decimal("0.01"))
    for i, (label, value) in enumerate(
        [("Net amount", net), ("VAT 19 %", vat), ("Amount due (EUR)", net + vat)]
    ):
        pdf.setFont("Helvetica-Bold" if i == 2 else "Helvetica", 9.5)
        pdf.drawString(125 * mm, y - 24 - i * 14, label)
        pdf.drawRightString(WIDTH - 20 * mm, y - 24 - i * 14, f"{value:,.2f}")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(
        20 * mm, 20 * mm, "Payable by bank transfer to IBAN DE00 9999 0000 1111 2222 33."
    )
    pdf.save()
    return target


# --------------------------------------------------------------------------- research note

NOTE_SECTIONS = [
    (
        "Abstract",
        [
            "We compare three fictional sorting heuristics on synthetic workloads. The results",
            "are invented for software testing and must not be cited. Values such as 0,95 and",
            "1.000 are written exactly as an author might, and an extractor must not 'fix' them.",
        ],
    ),
    (
        "1 Introduction",
        [
            "Document extraction tools are often evaluated on tidy inputs. This note instead mixes",
            "running text, a numbered section structure, a results table and a reference list,",
            "which is the minimum structure of most short scientific reports.",
        ],
    ),
    (
        "2 Method",
        [
            "Each heuristic was run five times on each of three workload sizes. We report the",
            "median runtime in milliseconds and the relative speed-up against the baseline.",
        ],
    ),
]
NOTE_TABLE = [
    ("Heuristic", "n = 1k (ms)", "n = 10k (ms)", "n = 100k (ms)", "Speed-up"),
    ("Baseline", "1.8", "22.4", "301.0", "1.00"),
    ("Bucketed", "1.2", "14.9", "187.5", "1.61"),
    ("Adaptive", "1.4", "13.1", "162.2", "1.86"),
]


def make_research_note(folder: Path) -> Path:
    target = folder / "demo_research_note.pdf"
    pdf = _canvas(target)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(WIDTH / 2, HEIGHT - 28 * mm, "Sorting Heuristics on Synthetic Workloads")
    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawCentredString(
        WIDTH / 2, HEIGHT - 35 * mm, "R. Placeholder and S. Sample, Example Institute"
    )
    y = HEIGHT - 50 * mm
    for heading, lines in NOTE_SECTIONS:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(25 * mm, y, heading)
        y -= 15
        pdf.setFont("Helvetica", 10)
        for line in lines:
            pdf.drawString(25 * mm, y, line)
            y -= 13
        y -= 8
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(25 * mm, y, "3 Results")
    y -= 10
    widths = (100, 80, 80, 85, 70)
    for r, row in enumerate(NOTE_TABLE):
        x = 25 * mm
        for width, value in zip(widths, row, strict=True):
            pdf.rect(x, y - 18, width, 18)
            pdf.setFont("Helvetica-Bold" if r == 0 else "Helvetica", 9)
            pdf.drawString(x + 4, y - 12, value)
            x += width
        y -= 18
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(25 * mm, y - 13, "Table 1: Median runtime over five runs (invented data).")
    pdf.showPage()

    y = HEIGHT - 28 * mm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(25 * mm, y, "4 Discussion")
    pdf.setFont("Helvetica", 10)
    for line in (
        "The adaptive heuristic is fastest for large inputs, while the bucketed",
        "variant wins for the smallest workload. Both claims hold only for this",
        "invented data set.",
    ):
        y -= 13
        pdf.drawString(25 * mm, y, line)
    y -= 26
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(25 * mm, y, "References")
    pdf.setFont("Helvetica", 9)
    for ref in (
        "[1] A. Author. An Imaginary Survey of Sorting. Journal of Examples, 2024.",
        "[2] B. Writer. Placeholder Benchmarks. Proc. Workshop on Fictional Data, 2025.",
    ):
        y -= 13
        pdf.drawString(25 * mm, y, ref)
    pdf.save()
    return target


# --------------------------------------------------------------------------- bank CSV export


def make_bank_export(folder: Path) -> Path:
    """German online-banking style: ';' delimiter, cp1252 (Windows) encoding, umlauts."""
    target = folder / "demo_bank_export.csv"
    rows = [
        (
            "Buchungstag",
            "Valuta",
            "Empfänger/Auftraggeber",
            "Verwendungszweck",
            "Betrag",
            "Währung",
        ),
        ("02.03.2026", "02.03.2026", "Example Employer GmbH", "Gehalt Februar", "3.250,00", "EUR"),
        ("04.03.2026", "05.03.2026", "Städtische Werke", "Abschlag Strom März", "-96,15", "EUR"),
        ("08.03.2026", "08.03.2026", "Bücherstube am Markt", "Kartenzahlung", "-23,90", "EUR"),
        ("14.03.2026", "14.03.2026", "Online Shop", "Erstattung Bestellung 99812", "29,99", "EUR"),
        ("21.03.2026", "21.03.2026", "Baumarkt Süd", "Kartenzahlung; Werkzeug", "-1.249,00", "EUR"),
        (
            "30.03.2026",
            "31.03.2026",
            "Northwind Example Bank",
            "Kontoführungsgebühr",
            "-4,95",
            "EUR",
        ),
    ]

    def quote(value: str) -> str:
        return f'"{value}"' if ";" in value or '"' in value else value

    text = "\r\n".join(";".join(quote(v) for v in row) for row in rows) + "\r\n"
    target.write_bytes(text.encode("cp1252"))
    return target


# --------------------------------------------------------------------------- statement without lines

# Day/month only; the year follows from the period printed in the header (Dec 2025 - Jan 2026).
LINELESS_ROWS = [
    ("1/12", "ABONO INTERESES AHORROS", "", "", "4.12"),
    ("2/12", "PAGO SUC VIRT TARJETA", "", "", "-320,000.00"),
    ("3/12", "RETIRO CAJERO CENTRO", "CENTRO", "", "-200,000.00"),
    ("5/12", "TRANSFERENCIA DESDE CUENTA", "", "", "1,250,000.00"),
    ("9/12", "AJUSTE INTERES AHORROS DB", "", "", "-.02"),
    ("12/12", "PAGO QR TIENDA EJEMPLO", "", "", "-48,500.00"),
    ("15/12", "PAGO SEGURO DE VIDA", "NORTE", "", "-22,169.00"),
    ("19/12", "COMPRA EN COMERCIO", "", "", "-75,000.00"),
    ("23/12", "TRANSFERENCIA CTA SUC VIRTUAL", "", "", "-430,000.00"),
    ("31/12", "ABONO INTERESES AHORROS", "", "", "3.87"),
    ("2/01", "PAGO QR CAFETERIA", "", "", "-12,000.00"),
    ("5/01", "RETIRO CAJERO NORTE", "NORTE", "", "-300,000.00"),
    ("8/01", "TRANSFERENCIA DESDE CUENTA", "", "", "900,000.00"),
    ("14/01", "PAGO SUC VIRT TARJETA", "", "", "-511,230.00"),
    ("20/01", "CUOTA MANEJO TARJETA", "", "", "-11,175.00"),
    ("27/01", "PAGO QR LIBRERIA", "", "", "-64,000.00"),
    ("31/01", "ABONO INTERESES AHORROS", "", "", "2.95"),
]
LINELESS_OPENING = Decimal("1500000.00")
LINELESS_COLUMNS = [  # header text, header x, alignment, value x
    ("FECHA", 40, "r", 70),
    ("DESCRIPCIÓN", 140, "l", 80),
    ("SUCURSAL", 290, "l", 285),
    ("DCTO.", 370, "l", 365),
    ("VALOR", 440, "r", 500),
    ("SALDO", 525, "r", 575),
]


def _co(amount: Decimal) -> str:
    """Format like the statement: 1,234.56, -.02, .00 (no leading zero below 1)."""
    text = f"{amount:,.2f}"
    return text.replace("0.", ".", 1) if abs(amount) < 1 else text


def make_lineless_statement(folder: Path) -> Path:
    target = folder / "demo_lineless_statement.pdf"
    pdf = _canvas(target)
    balance = LINELESS_OPENING
    rows = []
    for date_, desc, branch, doc, amount in LINELESS_ROWS:
        balance += Decimal(amount.replace(",", ""))
        rows.append((date_, desc, branch, doc, amount, _co(balance)))
    credits = sum(Decimal(r[4].replace(",", "")) for r in LINELESS_ROWS if not r[4].startswith("-"))
    debits = -sum(Decimal(r[4].replace(",", "")) for r in LINELESS_ROWS if r[4].startswith("-"))
    pages = [rows[:10], rows[10:]]
    for number, chunk in enumerate(pages, start=1):
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(40, 800, "Banco de Ejemplo")
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(330, 800, "ESTADO DE CUENTA")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(330, 785, "DESDE: 2025/11/30 HASTA: 2026/01/31")
        pdf.drawString(330, 772, "CUENTA DE AHORROS 000-000000-00")
        pdf.drawString(40, 772, "TITULAR DE EJEMPLO")
        y = 740
        if number == 1:
            pdf.setFont("Courier-Oblique", 8)
            summary = [
                ("SALDO ANTERIOR", LINELESS_OPENING),
                ("TOTAL ABONOS", credits),
                ("TOTAL CARGOS", debits),
                ("SALDO ACTUAL", balance),
            ]
            for label, value in summary:
                pdf.drawString(60, y, label)
                pdf.drawString(170, y, "$")
                pdf.drawRightString(300, y, _co(value))
                y -= 12
            y -= 14
        pdf.setFont("Helvetica-Bold", 9)
        for label, header_x, _, _ in LINELESS_COLUMNS:
            pdf.drawString(header_x, y, label)
        pdf.setFont("Courier", 8)
        for row in chunk:
            y -= 12
            for (_, _, align, value_x), value in zip(LINELESS_COLUMNS, row, strict=True):
                (pdf.drawRightString if align == "r" else pdf.drawString)(value_x, y, value)
        if number == len(pages):
            y -= 18
            pdf.drawString(80, y, "FIN ESTADO DE CUENTA")
        pdf.setFont("Helvetica", 6.5)
        pdf.drawString(40, 40, "DCF: defensor@banco-ejemplo.invalid; Banco de Ejemplo es ficticio.")
        pdf.setFont("Courier", 8)
        pdf.drawRightString(570, 28, f"PAGINA: {number}")
        pdf.showPage()
    pdf.save()
    return target


# --------------------------------------------------------------------------- original minimal fixtures


def make_minimal(folder: Path) -> list[Path]:
    tabular = folder / "demo_ruled.pdf"
    pdf = _canvas(tabular)
    rows = [
        ("Date", "Description", "Amount"),
        ("2026-01-02", "Book", "1000.00"),
        ("2026-01-03", "Meal", "-10.25"),
    ]
    for r, row in enumerate(rows):
        x = 50
        y = 760 - r * 30
        for width, value in zip((120, 200, 120), row, strict=True):
            pdf.rect(x, y - 30, width, 30)
            pdf.setFont("Helvetica", 10)
            pdf.drawString(x + 5, y - 20, value)
            x += width
    pdf.save()

    narrative = folder / "demo_narrative.pdf"
    pdf = _canvas(narrative)
    pdf.setFont("Helvetica", 16)
    pdf.drawString(52, 770, "A Short Example with a Tpyo")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(52, 735, "This fictional text contains a deliberate speling mistake.")
    pdf.drawString(52, 712, "The author stated 1.000,00 EUR, and this must not be corrected.")
    pdf.showPage()
    pdf.setFont("Helvetica", 14)
    pdf.drawString(52, 770, "Chapter Two")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(52, 735, "A second page tests page provenance.")
    pdf.save()

    csv_path = folder / "demo.csv"
    csv_path.write_text(
        'Datum,Beschreibung,Betrag\n02/11/2026,Book,"1.000,50"\n03/11/2026,Transport,"-45,80"\n',
        encoding="utf-8",
    )
    return [tabular, narrative, csv_path]


EXAMPLES = Path(__file__).resolve().parent


def generate() -> list[Path]:
    def data(name: str) -> Path:
        folder = EXAMPLES / name / "data"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    return [
        *make_minimal(data("01_quickstart")),
        make_research_note(data("02_research_note")),
        make_statement(data("03_bank_statement_pdf")),
        make_bank_export(data("04_bank_csv_export")),
        make_invoice(data("06_borderless_invoice")),
        make_lineless_statement(data("08_statement_without_lines")),
    ]


if __name__ == "__main__":
    for path in generate():
        print(f"wrote {path.relative_to(EXAMPLES.parent)}")
    if "--results" in sys.argv[1:]:
        sys.path.insert(0, str(EXAMPLES))
        from expected_results import write_all

        for path in write_all():
            print(f"wrote {path.relative_to(EXAMPLES.parent)}")
