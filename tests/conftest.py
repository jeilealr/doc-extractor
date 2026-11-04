"""Synthetic-only tests. Real bank statements remain outside the repository."""

from __future__ import annotations

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setFont("Helvetica", 13)
    pdf.drawString(50, 780, "A Research Paper with a Tpyographic Errror")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, 750, "The result was 1.000,00 EUR, as written.")
    pdf.drawString(50, 730, "The authors tested a synthetic observation.")
    pdf.showPage()
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, 780, "Chapter Two")
    pdf.drawString(50, 740, "Sentence with mistakes and an unusual mix of WORDS.")
    pdf.save()
    return path


@pytest.fixture
def ruled_pdf(tmp_path):
    path = tmp_path / "ruled.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    labels = [
        ["Date", "Description", "Amount"],
        ["2026-01-02", "Book", "1000.00"],
        ["2026-01-03", "Meal", "-10.25"],
    ]
    x0, y0 = 50, 760
    widths = [120, 200, 120]
    for row_index, values in enumerate(labels):
        top = y0 - row_index * 30
        x = x0
        for width, value in zip(widths, values, strict=True):
            pdf.rect(x, top - 30, width, 30)
            pdf.setFont("Helvetica", 10)
            pdf.drawString(x + 5, top - 21, value)
            x += width
    pdf.save()
    return path


@pytest.fixture
def borderless_pdf(tmp_path):
    path = tmp_path / "borderless.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setFont("Helvetica", 10)
    data = [
        ["Item", "Year", "Quantity"],
        ["Alpha", "2024", "12"],
        ["Beta", "2025", "33"],
        ["Gamma", "2026", "44"],
    ]
    for row, fields in enumerate(data):
        y = 780 - row * 28
        for x, value in zip((60, 240, 420), fields, strict=True):
            pdf.drawString(x, y, value)
    pdf.save()
    return path


@pytest.fixture
def payback_csv(tmp_path):
    path = tmp_path / "activity.csv"
    path.write_bytes(
        'Datum,Beschreibung,Betrag\n02/11/2026,Book purchase,"1.000,50"\n'
        '03/11/2026,Test item,"-45,80"\n'.encode("utf-8-sig")
    )
    return path
