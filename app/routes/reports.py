from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.models.transaction import Transaction
from app.models.category import Category
from app.services.reports import (
    generate_csv_report,
    generate_pdf_report,
    get_filtered_transactions_query,
)

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def parse_date(date_str: str | None) -> date | None:
    """Helper to safely parse YYYY-MM-DD date string."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


@reports_bp.route("/")
@login_required
def index():
    """Financial reporting dashboard with date filtering and export options."""
    start_date = parse_date(request.args.get("start_date"))
    end_date = parse_date(request.args.get("end_date"))
    trans_type = request.args.get("type", "all")

    query = get_filtered_transactions_query(current_user.id, start_date, end_date, trans_type)
    transactions = query.all()

    # Aggregate summaries
    total_income = sum((tx.amount for tx in transactions if tx.transaction_type == "income"), Decimal("0.00"))
    total_expenses = sum((tx.amount for tx in transactions if tx.transaction_type == "expense"), Decimal("0.00"))
    net_savings = total_income - total_expenses
    savings_rate = round((float(net_savings) / float(total_income) * 100.0), 1) if total_income > 0 else 0.0

    # Category breakdown for the filtered period
    cat_summary = (
        db.session.query(
            Category.name,
            Category.type,
            Category.color,
            func.coalesce(func.sum(Transaction.amount), 0).label("total_amount"),
            func.count(Transaction.id).label("tx_count"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(Transaction.user_id == current_user.id)
    )
    if start_date:
        cat_summary = cat_summary.filter(Transaction.transaction_date >= start_date)
    if end_date:
        cat_summary = cat_summary.filter(Transaction.transaction_date <= end_date)
    if trans_type in ["income", "expense"]:
        cat_summary = cat_summary.filter(Transaction.transaction_type == trans_type)

    cat_breakdown = cat_summary.group_by(Category.name, Category.type, Category.color).order_by(func.sum(Transaction.amount).desc()).all()

    return render_template(
        "reports/reports.html",
        transactions=transactions,
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        savings_rate=savings_rate,
        cat_breakdown=cat_breakdown,
        start_date=request.args.get("start_date", ""),
        end_date=request.args.get("end_date", ""),
        trans_type=trans_type,
    )


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    """Stream user financial transactions as an RFC 4180 CSV attachment."""
    start_date = parse_date(request.args.get("start_date"))
    end_date = parse_date(request.args.get("end_date"))
    trans_type = request.args.get("type", "all")

    csv_data = generate_csv_report(current_user, start_date, end_date, trans_type)
    filename = f"financial_statement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/export/pdf")
@login_required
def export_pdf():
    """Stream user financial statement as a formatted ReportLab PDF document."""
    start_date = parse_date(request.args.get("start_date"))
    end_date = parse_date(request.args.get("end_date"))

    pdf_bytes = generate_pdf_report(current_user, start_date, end_date)
    filename = f"financial_statement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
