from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Any
from sqlalchemy import func, extract
from app.extensions import db
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.category import Category


def get_monthly_summary(user_id: int, year: int, month: int) -> Dict[str, Any]:
    """
    Compute total income, total expenses, net savings, and savings rate
    for a specific user in a specific calendar month.
    """
    income = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        )
        .scalar()
    )
    expenses = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        )
        .scalar()
    )

    income_dec = Decimal(str(income or 0.00))
    expenses_dec = Decimal(str(expenses or 0.00))
    net_savings = income_dec - expenses_dec

    savings_rate = 0.0
    if income_dec > Decimal("0.00"):
        savings_rate = round((float(net_savings) / float(income_dec)) * 100.0, 1)

    return {
        "income": income_dec,
        "expenses": expenses_dec,
        "net_savings": net_savings,
        "savings_rate": savings_rate,
    }


def get_category_spending_breakdown(user_id: int, year: int, month: int) -> Dict[str, Any]:
    """
    Aggregate expenses by category for a given month to power Chart.js donut charts.
    Returns labels, amounts, colors, and percentages.
    """
    results = (
        db.session.query(
            Category.name,
            Category.color,
            Category.icon,
            func.coalesce(func.sum(Transaction.amount), 0).label("total_amount"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        )
        .group_by(Category.id, Category.name, Category.color, Category.icon)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    labels = []
    data = []
    colors = []
    categories_list = []
    total_spent = sum(r.total_amount for r in results) if results else Decimal("0.00")

    for r in results:
        amt = float(r.total_amount)
        labels.append(r.name)
        data.append(round(amt, 2))
        colors.append(r.color or "#4e73df")
        pct = (float(r.total_amount) / float(total_spent) * 100.0) if total_spent > 0 else 0.0
        categories_list.append({
            "name": r.name,
            "amount": float(r.total_amount),
            "color": r.color,
            "icon": r.icon,
            "percentage": round(pct, 1),
        })

    return {
        "labels": labels,
        "data": data,
        "colors": colors,
        "categories": categories_list,
        "total_spent": float(total_spent),
    }


def get_six_month_trend(user_id: int) -> Dict[str, Any]:
    """
    Generate month-by-month Income vs. Expense trend data for the last 6 calendar months.
    Powers Chart.js comparative bar and line charts.
    """
    today = date.today()
    labels = []
    income_data = []
    expense_data = []

    # Generate sequential list of past 6 months (oldest to newest)
    month_tuples = []
    curr_year, curr_month = today.year, today.month
    for _ in range(6):
        month_tuples.append((curr_year, curr_month))
        curr_month -= 1
        if curr_month == 0:
            curr_month = 12
            curr_year -= 1

    month_tuples.reverse()  # Oldest first

    for yr, mo in month_tuples:
        dt = datetime(yr, mo, 1)
        labels.append(dt.strftime("%b %Y"))

        inc = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "income",
                extract("year", Transaction.transaction_date) == yr,
                extract("month", Transaction.transaction_date) == mo,
            )
            .scalar()
        )
        exp = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "expense",
                extract("year", Transaction.transaction_date) == yr,
                extract("month", Transaction.transaction_date) == mo,
            )
            .scalar()
        )

        income_data.append(float(inc or 0.00))
        expense_data.append(float(exp or 0.00))

    return {
        "labels": labels,
        "income": income_data,
        "expenses": expense_data,
    }


def get_budget_performance(user_id: int, year: int, month: int) -> Dict[str, Any]:
    """
    Compare category budget allocations vs actual spending for the specified month.
    Powers horizontal comparison charts.
    """
    budgets = (
        Budget.query.filter_by(user_id=user_id, month=month, year=year)
        .join(Category)
        .order_by(Budget.amount_limit.desc())
        .all()
    )

    labels = []
    allocated_limits = []
    actual_spent = []

    for b in budgets:
        spent = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == user_id,
                Transaction.category_id == b.category_id,
                Transaction.transaction_type == "expense",
                extract("year", Transaction.transaction_date) == year,
                extract("month", Transaction.transaction_date) == month,
            )
            .scalar()
        )
        labels.append(b.category.name)
        allocated_limits.append(float(b.amount_limit))
        actual_spent.append(float(spent or 0.00))

    return {
        "labels": labels,
        "allocated": allocated_limits,
        "actual": actual_spent,
    }


def get_mom_expense_variance(user_id: int, year: int, month: int) -> Dict[str, Any]:
    """
    Compute Month-over-Month (MoM) expense variance comparing current month with previous month.
    Formula: MoM % = ((Current Expenses - Previous Expenses) / Previous Expenses) * 100
    """
    current_summary = get_monthly_summary(user_id, year, month)
    curr_exp = current_summary["expenses"]

    # Calculate previous month and year
    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year

    prev_summary = get_monthly_summary(user_id, prev_year, prev_month)
    prev_exp = prev_summary["expenses"]

    diff_amount = curr_exp - prev_exp
    pct_change = 0.0

    if prev_exp > Decimal("0.00"):
        pct_change = round(((float(curr_exp) - float(prev_exp)) / float(prev_exp)) * 100.0, 1)

    return {
        "current_expenses": curr_exp,
        "previous_expenses": prev_exp,
        "difference": diff_amount,
        "percentage_change": pct_change,
        "is_increase": diff_amount > Decimal("0.00"),
    }
