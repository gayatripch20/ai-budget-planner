from datetime import date
from decimal import Decimal
import json
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from app.extensions import db
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import FinancialGoal
from app.models.notification import Notification
from app.services.analytics import (
    get_monthly_summary,
    get_category_spending_breakdown,
    get_six_month_trend,
)

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    """Executive Personal Finance Dashboard with live KPI widgets and Chart.js feeds."""
    today = date.today()
    current_year, current_month = today.year, today.month

    # 1. Month-to-Date (MTD) financial summary
    summary = get_monthly_summary(current_user.id, current_year, current_month)

    # 2. Overall budget utilization for current month
    budgets = Budget.query.filter_by(user_id=current_user.id, month=current_month, year=current_year).all()
    total_budget_limit = sum(b.amount_limit for b in budgets) if budgets else Decimal("0.00")
    total_budget_spent = Decimal("0.00")
    for b in budgets:
        spent = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.category_id == b.category_id,
                Transaction.transaction_type == "expense",
                extract("year", Transaction.transaction_date) == current_year,
                extract("month", Transaction.transaction_date) == current_month,
            )
            .scalar()
        )
        total_budget_spent += Decimal(str(spent or 0.00))

    budget_utilization_pct = 0.0
    if total_budget_limit > Decimal("0.00"):
        budget_utilization_pct = round((float(total_budget_spent) / float(total_budget_limit)) * 100.0, 1)

    # 3. Recent Transactions (latest 6)
    recent_transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(6)
        .all()
    )

    # 4. Active Financial Goals
    active_goals = (
        FinancialGoal.query.filter_by(user_id=current_user.id)
        .filter(FinancialGoal.status != "completed")
        .order_by(FinancialGoal.target_date.asc())
        .limit(4)
        .all()
    )

    # 5. Unread Notifications
    unread_notifications = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    # 6. Chart.js Data Payloads
    category_breakdown = get_category_spending_breakdown(current_user.id, current_year, current_month)
    trend_data = get_six_month_trend(current_user.id)

    return render_template(
        "dashboard/index.html",
        summary=summary,
        total_budget_limit=total_budget_limit,
        total_budget_spent=total_budget_spent,
        budget_utilization_pct=budget_utilization_pct,
        budget_utilization_bar=min(100.0, max(0.0, budget_utilization_pct)),
        has_budgets=len(budgets) > 0,
        recent_transactions=recent_transactions,
        active_goals=active_goals,
        unread_notifications=unread_notifications,
        category_chart_json=json.dumps(category_breakdown, default=float),
        trend_chart_json=json.dumps(trend_data, default=float),
        current_month_name=today.strftime("%B %Y"),
    )


@dashboard_bp.route("/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notif_id: int):
    """Mark a single notification as read."""
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    flash("Notification marked as read.", "info")
    return redirect(request.referrer or url_for("dashboard.index"))


@dashboard_bp.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    """Mark all unread notifications as read for current user."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications cleared.", "info")
    return redirect(request.referrer or url_for("dashboard.index"))
