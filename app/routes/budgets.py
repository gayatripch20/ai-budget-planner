from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from app.extensions import db
from app.models.category import Category
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.notification import Notification
from app.forms.budget import BudgetForm

budgets_bp = Blueprint("budgets", __name__, url_prefix="/budgets")


def get_expense_categories():
    """Retrieve expense categories available to the authenticated user."""
    return (
        Category.query.filter(
            Category.type == "expense",
            or_(Category.user_id.is_(None), Category.user_id == current_user.id),
        )
        .order_by(Category.name.asc())
        .all()
    )


@budgets_bp.route("/")
@login_required
def index():
    """Display budget planner and category utilization metrics for the selected month/year."""
    today = date.today()
    selected_month = request.args.get("month", today.month, type=int)
    selected_year = request.args.get("year", today.year, type=int)

    # Validate month
    if not (1 <= selected_month <= 12):
        selected_month = today.month

    # Query all budgets defined by user for this month/year
    budgets = (
        Budget.query.filter_by(user_id=current_user.id, month=selected_month, year=selected_year)
        .join(Category)
        .order_by(Category.name.asc())
        .all()
    )

    budget_items = []
    total_budgeted = Decimal("0.00")
    total_spent = Decimal("0.00")

    for b in budgets:
        # Sum actual expenses in this category for the given month/year
        spent = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.category_id == b.category_id,
                Transaction.transaction_type == "expense",
                func.extract("month", Transaction.transaction_date) == selected_month,
                func.extract("year", Transaction.transaction_date) == selected_year,
            )
            .scalar()
        )
        spent_dec = Decimal(str(spent or 0.00))
        limit_dec = Decimal(str(b.amount_limit))

        total_budgeted += limit_dec
        total_spent += spent_dec

        remaining_dec = limit_dec - spent_dec
        pct = (float(spent_dec) / float(limit_dec) * 100.0) if limit_dec > 0 else 0.0
        pct_capped = min(100.0, max(0.0, pct))

        # Status and color mapping
        if pct >= 100.0:
            status = "danger"
            status_text = "Exceeded"
            # Trigger alert notification if in current month
            if selected_month == today.month and selected_year == today.year:
                alert_title = f"Budget Alert: {b.category.name} Exceeded!"
                existing_alert = Notification.query.filter_by(user_id=current_user.id, title=alert_title).first()
                if not existing_alert:
                    db.session.add(
                        Notification(
                            user_id=current_user.id,
                            title=alert_title,
                            message=f"You have spent {current_user.currency}{spent_dec} on {b.category.name}, exceeding your monthly limit of {current_user.currency}{limit_dec}!",
                            notification_type="danger",
                        )
                    )
                    db.session.commit()
        elif pct >= 80.0:
            status = "warning"
            status_text = "Near Limit (≥80%)"
            if selected_month == today.month and selected_year == today.year:
                alert_title = f"Budget Warning: {b.category.name} at {round(pct)}%"
                existing_alert = Notification.query.filter_by(user_id=current_user.id, title=alert_title).first()
                if not existing_alert:
                    db.session.add(
                        Notification(
                            user_id=current_user.id,
                            title=alert_title,
                            message=f"You have consumed {round(pct)}% of your {b.category.name} budget for this month ({current_user.currency}{spent_dec} / {current_user.currency}{limit_dec}).",
                            notification_type="warning",
                        )
                    )
                    db.session.commit()
        else:
            status = "success"
            status_text = "On Track"

        budget_items.append({
            "budget": b,
            "spent": spent_dec,
            "remaining": remaining_dec,
            "percentage": round(pct, 1),
            "percentage_bar": round(pct_capped, 1),
            "status": status,
            "status_text": status_text,
        })

    total_remaining = total_budgeted - total_spent
    overall_pct = (float(total_spent) / float(total_budgeted) * 100.0) if total_budgeted > 0 else 0.0

    return render_template(
        "budgets/budget_planner.html",
        budget_items=budget_items,
        selected_month=selected_month,
        selected_year=selected_year,
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        total_remaining=total_remaining,
        overall_percentage=round(overall_pct, 1),
        overall_percentage_bar=round(min(100.0, max(0.0, overall_pct)), 1),
    )


@budgets_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_budget():
    """Create a new monthly category budget cap."""
    form = BudgetForm()
    categories = get_expense_categories()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        # Check for duplicate budget in the same category/month/year
        existing = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=form.category_id.data,
            month=form.month.data,
            year=form.year.data,
        ).first()

        if existing:
            flash(
                "A budget for this category already exists in the selected month/year. You can update its limit instead.",
                "warning",
            )
            return redirect(url_for("budgets.index", month=form.month.data, year=form.year.data))

        budget = Budget(
            user_id=current_user.id,
            category_id=form.category_id.data,
            month=form.month.data,
            year=form.year.data,
            amount_limit=form.amount_limit.data,
        )
        db.session.add(budget)
        db.session.commit()

        flash("Budget created successfully!", "success")
        return redirect(url_for("budgets.index", month=form.month.data, year=form.year.data))

    return render_template("budgets/budget_form.html", form=form, action="Create")


@budgets_bp.route("/<int:budget_id>/edit", methods=["GET", "POST"])
@login_required
def edit_budget(budget_id: int):
    """Edit an existing budget with user ownership validation."""
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()

    form = BudgetForm(obj=budget)
    categories = get_expense_categories()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        budget.amount_limit = form.amount_limit.data
        budget.category_id = form.category_id.data
        budget.month = form.month.data
        budget.year = form.year.data

        db.session.commit()
        flash("Budget limit updated successfully!", "success")
        return redirect(url_for("budgets.index", month=budget.month, year=budget.year))

    return render_template("budgets/budget_form.html", form=form, action="Edit", budget=budget)


@budgets_bp.route("/<int:budget_id>/delete", methods=["POST"])
@login_required
def delete_budget(budget_id: int):
    """Delete a budget with user ownership verification and CSRF protection."""
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
    month, year = budget.month, budget.year

    db.session.delete(budget)
    db.session.commit()

    flash("Budget deleted successfully.", "info")
    return redirect(url_for("budgets.index", month=month, year=year))
