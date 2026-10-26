from datetime import date
from decimal import Decimal
import json
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.services.analytics import (
    get_monthly_summary,
    get_category_spending_breakdown,
    get_six_month_trend,
    get_budget_performance,
    get_mom_expense_variance,
)

analytics_bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@analytics_bp.route("/")
@login_required
def index():
    """In-depth Financial Analytics and Chart Visualizations."""
    today = date.today()
    selected_month = request.args.get("month", today.month, type=int)
    selected_year = request.args.get("year", today.year, type=int)

    if not (1 <= selected_month <= 12):
        selected_month = today.month

    # Retrieve analytical calculations from pure service layer
    summary = get_monthly_summary(current_user.id, selected_year, selected_month)
    mom_variance = get_mom_expense_variance(current_user.id, selected_year, selected_month)
    category_breakdown = get_category_spending_breakdown(current_user.id, selected_year, selected_month)
    six_month_trend = get_six_month_trend(current_user.id)
    budget_performance = get_budget_performance(current_user.id, selected_year, selected_month)

    return render_template(
        "analytics/analytics.html",
        selected_month=selected_month,
        selected_year=selected_year,
        summary=summary,
        mom_variance=mom_variance,
        category_breakdown=category_breakdown,
        category_chart_json=json.dumps(category_breakdown, default=float),
        trend_chart_json=json.dumps(six_month_trend, default=float),
        budget_chart_json=json.dumps(budget_performance, default=float),
    )
