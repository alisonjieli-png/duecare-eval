"""Shared manuscript and PDF layout for the DueCare evidence report."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

NAVY = colors.HexColor("#173749")
TEAL = colors.HexColor("#177E89")
MUTED = colors.HexColor("#536776")
WIDTH = 491


class Report:
    def __init__(self, root, title, subtitle, stamp):
        self.root, self.stamp = Path(root), stamp
        self.styles = {
            "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=28, leading=32, textColor=NAVY, spaceAfter=15),
            "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=13, leading=18, textColor=TEAL, spaceAfter=18),
            "page": ParagraphStyle("page", fontName="Helvetica-Bold", fontSize=19, leading=24, textColor=NAVY, spaceAfter=15),
            "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=TEAL, spaceBefore=10, spaceAfter=7, keepWithNext=True),
            "question": ParagraphStyle("question", fontName="Helvetica-Bold", fontSize=10.7, leading=14, textColor=TEAL, spaceBefore=7, spaceAfter=5, keepWithNext=True),
            "text": ParagraphStyle("text", fontName="Helvetica", fontSize=9.6, leading=13.5, spaceAfter=9, textColor=NAVY),
            "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8, leading=10.5, spaceAfter=7, textColor=MUTED),
            "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.1, leading=10.5, textColor=NAVY),
            "white": ParagraphStyle("white", fontName="Helvetica-Bold", fontSize=8.1, leading=10.5, textColor=colors.white),
        }
        self.story = [self.para(title, "title"), self.para(subtitle, "subtitle")]
        self.md = ["# " + title, "", subtitle, ""]
        self.title = title

    def para(self, text, style="text"):
        return Paragraph(escape(str(text)), self.styles[style])

    def text(self, text, small=False):
        self.story.append(self.para(text, "small" if small else "text"))
        self.md.extend([str(text), ""])

    def heading(self, text):
        self.story.append(self.para(text, "heading"))
        self.md.extend(["### " + text, ""])

    def page(self, title):
        self.story.extend([PageBreak(), self.para(title, "page")])
        self.md.extend(["## " + title, ""])

    def table(self, headers, rows, widths=None, padding=6):
        widths = widths or [WIDTH / len(headers)] * len(headers)
        if abs(sum(widths) - WIDTH) > .1:
            raise ValueError("Table widths must fill the report text area")
        cells = [[self.para(c, "white") for c in headers]]
        cells += [[self.para(c, "cell") for c in row] for row in rows]
        tab = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
        tab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F0F5F7"), colors.white]),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), padding),
            ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ]))
        self.story.extend([tab, Spacer(1, 10)])
        clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
        self.md.extend(["| " + " | ".join(map(clean, headers)) + " |", "| " + " | ".join("---" for _ in headers) + " |"])
        self.md.extend("| " + " | ".join(map(clean, row)) + " |" for row in rows)
        self.md.append("")

    def figure(self, name, caption, height):
        self.story.extend([Image(str(self.root / "docs/figures" / name), width=WIDTH, height=height), self.para(caption, "small")])
        self.md.extend([f"![{caption}](figures/{name})", ""])

    def question(self, identity, question, detail):
        self.story.append(KeepTogether([
            self.para(identity, "question"), self.para(question), self.para(detail, "small"),
        ]))
        self.md.extend(["#### " + identity, "", question, "", detail, ""])

    def write(self, manuscript_path="docs/PAPER.md", pdf_path="output/pdf/duecare_preliminary_report.pdf"):
        (self.root / manuscript_path).write_text("\n".join(self.md))
        output = self.root / pdf_path
        output.parent.mkdir(parents=True, exist_ok=True)

        def footer(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#ADC5D0"))
            canvas.line(52, 799, 543, 799)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(MUTED)
            canvas.drawString(52, 811, "DUECARE / MODEL BENCHMARK / SEPTEMBER 2026")
            canvas.drawString(52, 29, self.stamp)
            canvas.drawRightString(543, 29, str(doc.page))
            canvas.restoreState()

        SimpleDocTemplate(str(output), pagesize=A4, rightMargin=52, leftMargin=52,
                          topMargin=59, bottomMargin=49, title=self.title,
                          author="Taylor S. Amarel").build(self.story, onFirstPage=footer, onLaterPages=footer)
        return output
