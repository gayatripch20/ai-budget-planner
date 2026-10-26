"""
Academic Documentation PDF Generator for AI-Based Personal Budget Planning & Financial Goal System
Generates a publication-grade, styled MCA Final Project Documentation PDF using ReportLab.
"""
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Preformatted
)
from reportlab.pdfgen import canvas

PRIMARY = colors.HexColor("#1A365D")    # Deep Navy
SECONDARY = colors.HexColor("#2B6CB0")  # Slate Blue
ACCENT = colors.HexColor("#2C7A7B")     # Deep Teal
TEXT_DARK = colors.HexColor("#2D3748")  # Charcoal
TEXT_MUTED = colors.HexColor("#718096") # Muted Gray
BG_LIGHT = colors.HexColor("#F7FAFC")   # Light Background
BORDER_COLOR = colors.HexColor("#E2E8F0")

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page count and professional running headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages):
        width, height = A4
        # Omit header and footer on Page 1 (Cover Page)
        if self._pageNumber > 1:
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(TEXT_MUTED)
            # Running header
            self.drawString(54, height - 36, "AI-Based Personal Budget Planning & Financial Goal System")
            self.drawRightString(width - 54, height - 36, "MCA Final Project Documentation")
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.6)
            self.line(54, height - 42, width - 54, height - 42)

            # Running footer
            self.line(54, 45, width - 54, 45)
            self.drawString(54, 32, "Confidential — Academic Master of Computer Applications (MCA) Project")
            self.drawRightString(width - 54, 32, f"Page {self._pageNumber} of {total_pages}")
            self.restoreState()

def create_documentation_pdf(input_md_path, output_pdf_path):
    with open(input_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=PRIMARY,
        alignment=1, # Center
        spaceAfter=15
    ))

    styles.add(ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=SECONDARY,
        alignment=1,
        spaceAfter=25
    ))

    styles.add(ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=16,
        textColor=TEXT_DARK,
        alignment=1
    ))

    styles.add(ParagraphStyle(
        'DocH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        'DocH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        'DocH3',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=ACCENT,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=TEXT_DARK,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    ))

    styles.add(ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=TEXT_DARK
    ))

    styles.add(ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.white
    ))

    styles.add(ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1A202C")
    ))

    story = []

    # ==================== 1. COVER PAGE ====================
    story.append(Spacer(1, 40))
    # Academic Header Banner
    story.append(Paragraph("ACADEMIC PROJECT DOCUMENTATION REPORT", ParagraphStyle(
        'CoverPre', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=ACCENT, alignment=1, spaceAfter=15
    )))
    story.append(Paragraph("AI-Based Personal Budget Planning &amp; Financial Goal System", styles['CoverTitle']))
    story.append(Paragraph("A Multi-Tenant Financial Analytics &amp; Machine Learning Web Platform", styles['CoverSubtitle']))

    # Divider Table
    divider = Table([[""]], colWidths=[475], rowHeights=[3])
    divider.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), SECONDARY)]))
    story.append(divider)
    story.append(Spacer(1, 30))

    meta_table_data = [
        [Paragraph("<b>Degree Program:</b>", styles['DocBody']), Paragraph("Master of Computer Applications (MCA)", styles['DocBody'])],
        [Paragraph("<b>Course Focus:</b>", styles['DocBody']), Paragraph("Final Semester Major Capstone Project", styles['DocBody'])],
        [Paragraph("<b>Author / Candidate:</b>", styles['DocBody']), Paragraph("Gayatri Chokhani (GitHub: <b>@gayatripch20</b>)", styles['DocBody'])],
        [Paragraph("<b>Repository:</b>", styles['DocBody']), Paragraph("https://github.com/gayatripch20/ai-budget-planner", styles['DocBody'])],
        [Paragraph("<b>Technology Stack:</b>", styles['DocBody']), Paragraph("Python 3.14, Flask 3.1, MySQL 8.0, Scikit-Learn, Pandas, Bootstrap 5, Chart.js, ReportLab", styles['DocBody'])],
        [Paragraph("<b>Verification Matrix:</b>", styles['DocBody']), Paragraph("49 / 49 Pytest Test Cases Passing (100% Pass Rate)", styles['DocBody'])],
        [Paragraph("<b>Architecture:</b>", styles['DocBody']), Paragraph("Three-Tier MVC / Service-Oriented Multi-Tenant Architecture", styles['DocBody'])],
        [Paragraph("<b>Academic Year:</b>", styles['DocBody']), Paragraph("2026", styles['DocBody'])],
    ]
    meta_table = Table(meta_table_data, colWidths=[130, 345])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 40))
    exec_summary_box = [
        [Paragraph("<b>EXECUTIVE SUMMARY &amp; VIVA HIGHLIGHTS</b>", ParagraphStyle('Bld', fontName='Helvetica-Bold', fontSize=9, textColor=PRIMARY))],
        [Paragraph(
            "This document constitutes the official academic report and technical reference for the "
            "<b>AI-Based Personal Budget Planning &amp; Financial Goal System</b>. Built ground-up "
            "without third-party template clones, it features strict decimal accounting precision, "
            "multi-tenant data isolation (IDOR-safe), automated 80%/100% budget threshold alerts, "
            "mathematical milestone goal amortization, and an academic Scikit-learn multi-tier forecasting "
            "engine evaluated via Mean Absolute Error (MAE).", styles['DocBody']
        )]
    ]
    summary_table = Table(exec_summary_box, colWidths=[475])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EBF8FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BEE3F8")),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(summary_table)

    story.append(PageBreak())

    # ==================== 2. PARSE MARKDOWN CONTENT ====================
    lines = md_text.splitlines()
    i = 0
    in_code_block = False
    code_lines = []
    in_table = False
    table_rows = []

    def clean_inline_md(text):
        # Convert markdown bold/italic/code to reportlab tags
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Restore safe tags
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        text = re.sub(r'`(.+?)`', r'<font face="Courier" color="#1A365D"><b>\1</b></font>', text)
        text = text.replace(r'\$', '$')
        return text

    while i < len(lines):
        line = lines[i].rstrip()

        # Handle Code / Mermaid blocks
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lines = []
                i += 1
                continue
            else:
                in_code_block = False
                if code_lines:
                    # Chunk code into at most 25 lines so ReportLab can paginate smoothly
                    chunk_size = 25
                    for chunk_idx in range(0, len(code_lines), chunk_size):
                        chunk = code_lines[chunk_idx:chunk_idx + chunk_size]
                        chunk_text = "\n".join(chunk)
                        code_p = Preformatted(chunk_text, styles['CodeSnippet'])
                        code_box = Table([[code_p]], colWidths=[475])
                        code_box.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                            ('BOX', (0,0), (-1,-1), 0.75, BORDER_COLOR),
                            ('PADDING', (0,0), (-1,-1), 6),
                        ]))
                        story.append(Spacer(1, 3))
                        story.append(code_box)
                    story.append(Spacer(1, 6))
                i += 1
                continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Handle Tables
        if "|" in line and not line.startswith("```"):
            # Check if table separator line
            stripped = line.strip()
            if re.match(r'^\|?[\s:\-]+\|[\s:\-|]+$', stripped):
                i += 1
                continue
            cols = [c.strip() for c in stripped.strip('|').split('|')]
            if len(cols) > 1:
                table_rows.append(cols)
                # Lookahead to see if table continues
                if i + 1 >= len(lines) or "|" not in lines[i+1]:
                    # Process completed table
                    if len(table_rows) > 0:
                        num_cols = len(table_rows[0])
                        # Calculate column widths
                        col_width = 475 / num_cols
                        processed_table_data = []
                        for r_idx, row in enumerate(table_rows):
                            p_row = []
                            for c_idx, cell in enumerate(row):
                                cell_clean = clean_inline_md(cell)
                                if r_idx == 0:
                                    p_row.append(Paragraph(f"<b>{cell_clean}</b>", styles['TableHeader']))
                                else:
                                    p_row.append(Paragraph(cell_clean, styles['TableCell']))
                            # Pad row if incomplete
                            while len(p_row) < num_cols:
                                p_row.append(Paragraph("", styles['TableCell']))
                            processed_table_data.append(p_row[:num_cols])

                        t = Table(processed_table_data, colWidths=[col_width]*num_cols)
                        t.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), SECONDARY),
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('TOPPADDING', (0,0), (-1,-1), 4),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                            ('LEFTPADDING', (0,0), (-1,-1), 4),
                            ('RIGHTPADDING', (0,0), (-1,-1), 4),
                            ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
                            ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
                            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT])
                        ]))
                        story.append(Spacer(1, 4))
                        story.append(t)
                        story.append(Spacer(1, 6))
                        table_rows = []
                i += 1
                continue

        # Skip raw markdown metadata header on page 2 since we already have the cover
        if line.startswith("# ACADEMIC PROJECT REPORT") or line.startswith("## Title:"):
            i += 1
            continue

        # Horizontal Rule
        if line.strip() in ["---", "***", "___"]:
            rule = Table([[""]], colWidths=[475], rowHeights=[1])
            rule.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), BORDER_COLOR)]))
            story.append(Spacer(1, 6))
            story.append(rule)
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Headings
        if line.startswith("## "):
            h_text = clean_inline_md(line[3:].strip())
            story.append(Paragraph(h_text, styles['DocH1']))
            i += 1
            continue
        elif line.startswith("### "):
            h_text = clean_inline_md(line[4:].strip())
            story.append(Paragraph(h_text, styles['DocH2']))
            i += 1
            continue
        elif line.startswith("#### "):
            h_text = clean_inline_md(line[5:].strip())
            story.append(Paragraph(h_text, styles['DocH3']))
            i += 1
            continue

        # Bullet points
        if line.strip().startswith("- ") or line.strip().startswith("* "):
            bullet_text = clean_inline_md(line.strip()[2:].strip())
            story.append(Paragraph(f"• {bullet_text}", styles['DocBullet']))
            i += 1
            continue

        # Numbered list
        m_num = re.match(r'^\s*(\d+)\.\s+(.*)$', line)
        if m_num:
            num_val = m_num.group(1)
            item_text = clean_inline_md(m_num.group(2).strip())
            story.append(Paragraph(f"<b>{num_val}.</b> {item_text}", styles['DocBullet']))
            i += 1
            continue

        # Normal Paragraph
        clean_text = line.strip()
        if clean_text:
            story.append(Paragraph(clean_inline_md(clean_text), styles['DocBody']))
        else:
            story.append(Spacer(1, 3))

        i += 1

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Successfully built {output_pdf_path} (Size: {os.path.getsize(output_pdf_path):,} bytes)")

if __name__ == "__main__":
    base_dir = r"C:\Users\chokh\.gemini\antigravity\scratch\ai_budget_planner"
    md_in = os.path.join(base_dir, "docs", "MCA_PROJECT_REPORT.md")
    pdf_out = os.path.join(base_dir, "docs", "MCA_PROJECT_DOCUMENTATION.pdf")
    static_docs = os.path.join(base_dir, "app", "static", "docs")
    os.makedirs(static_docs, exist_ok=True)
    static_pdf = os.path.join(static_docs, "MCA_PROJECT_DOCUMENTATION.pdf")

    create_documentation_pdf(md_in, pdf_out)
    
    # Also copy to static folder for direct download
    import shutil
    shutil.copyfile(pdf_out, static_pdf)
    print(f"[OK] Also deployed to static web download: {static_pdf}")
