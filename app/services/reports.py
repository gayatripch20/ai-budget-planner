import io
import csv
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.extensions import db
from app.models.transaction import Transaction
from app.models.goal import FinancialGoal
from app.models.category import Category


def get_filtered_transactions_query(user_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None, trans_type: Optional[str] = None):
    """Construct filtered SQLAlchemy query for user transactions."""
    query = Transaction.query.filter(Transaction.user_id == user_id)
    if trans_type and trans_type in ["income", "expense"]:
        query = query.filter(Transaction.transaction_type == trans_type)
    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    return query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())


def generate_csv_report(user, start_date: Optional[date] = None, end_date: Optional[date] = None, trans_type: Optional[str] = None) -> str:
    """Generate RFC 4180 compliant CSV string of user transactions."""
    query = get_filtered_transactions_query(user.id, start_date, end_date, trans_type)
    transactions = query.all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV Header
    writer.writerow([
        "Transaction ID",
        "Date",
        "Type",
        "Category",
        "Payment Method",
        f"Amount ({user.currency})",
        "Description",
    ])

    for tx in transactions:
        writer.writerow([
            tx.id,
            tx.transaction_date.strftime("%Y-%m-%d"),
            tx.transaction_type.capitalize(),
            tx.category.name if tx.category else "Uncategorized",
            tx.payment_method,
            f"{tx.amount:.2f}",
            tx.description or "",
        ])

    return output.getvalue()


def generate_pdf_report(user, start_date: Optional[date] = None, end_date: Optional[date] = None) -> bytes:
    """
    Generate an in-memory PDF financial audit report using ReportLab.
    Includes document metadata, executive summary table, and detailed transaction ledger.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#4f46e5"),
        spaceBefore=12,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )

    story = []

    # 1. Header & Metadata
    story.append(Paragraph("Personal Financial Statement & Audit Report", title_style))
    date_range_str = "All Time"
    if start_date and end_date:
        date_range_str = f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
    elif start_date:
        date_range_str = f"From {start_date.strftime('%d %b %Y')}"
    elif end_date:
        date_range_str = f"Up to {end_date.strftime('%d %b %Y')}"

    meta_text = (
        f"<b>Account Holder:</b> {user.full_name} ({user.email}) &bull; "
        f"<b>Date Range:</b> {date_range_str} &bull; "
        f"<b>Generated:</b> {datetime.now().strftime('%d %b %Y, %H:%M')}"
    )
    story.append(Paragraph(meta_text, subtitle_style))
    story.append(Spacer(1, 14))

    # 2. Executive Financial Summary
    query = get_filtered_transactions_query(user.id, start_date, end_date)
    transactions = query.all()

    total_income = sum((tx.amount for tx in transactions if tx.transaction_type == "income"), Decimal("0.00"))
    total_expenses = sum((tx.amount for tx in transactions if tx.transaction_type == "expense"), Decimal("0.00"))
    net_savings = total_income - total_expenses
    savings_rate = round((float(net_savings) / float(total_income) * 100.0), 1) if total_income > 0 else 0.0

    story.append(Paragraph("1. Executive Summary", heading_style))
    summary_data = [
        ["Total Income", "Total Expenses", "Net Savings Balance", "Savings Rate"],
        [
            f"{user.currency} {total_income:,.2f}",
            f"{user.currency} {total_expenses:,.2f}",
            f"{user.currency} {net_savings:,.2f}",
            f"{savings_rate}%",
        ],
    ]
    summary_table = Table(summary_data, colWidths=[130, 130, 140, 120])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 1), (0, 1), colors.HexColor("#16a34a")),
        ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#dc2626")),
        ("TEXTCOLOR", (2, 1), (2, 1), colors.HexColor("#4f46e5")),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # 3. Detailed Transaction Ledger
    story.append(Paragraph(f"2. Detailed Transaction Ledger ({len(transactions)} Records)", heading_style))
    ledger_data = [
        ["Date", "Type", "Category", "Method", "Description", f"Amount ({user.currency})"]
    ]

    for tx in transactions:
        desc_p = Paragraph(tx.description or "—", cell_style)
        amt_str = f"+{tx.amount:,.2f}" if tx.transaction_type == "income" else f"-{tx.amount:,.2f}"
        ledger_data.append([
            tx.transaction_date.strftime("%d-%m-%Y"),
            tx.transaction_type.capitalize(),
            tx.category.name if tx.category else "—",
            tx.payment_method,
            desc_p,
            amt_str,
        ])

    if len(ledger_data) == 1:
        ledger_data.append(["—", "—", "—", "—", Paragraph("No transactions recorded in this period.", cell_style), "0.00"])

    ledger_table = Table(ledger_data, colWidths=[65, 55, 100, 75, 145, 80], repeatRows=1)
    ledger_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (3, -1), "LEFT"),
        ("ALIGN", (5, 0), (5, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(ledger_table)

    # Build document
    doc.build(story)
    return buffer.getvalue()
