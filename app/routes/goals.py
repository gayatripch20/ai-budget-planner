from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.goal import FinancialGoal, SavingsContribution
from app.models.notification import Notification
from app.forms.goal import FinancialGoalForm, SavingsContributionForm

goals_bp = Blueprint("goals", __name__, url_prefix="/goals")


@goals_bp.route("/")
@login_required
def index():
    """List all financial goals with real-time amortization calculations and status updates."""
    goals = FinancialGoal.query.filter_by(user_id=current_user.id).order_by(FinancialGoal.target_date.asc()).all()

    today = date.today()
    total_target = Decimal("0.00")
    total_saved = Decimal("0.00")

    # Update statuses dynamically
    for g in goals:
        total_target += Decimal(str(g.target_amount))
        total_saved += Decimal(str(g.current_amount))

        if g.current_amount >= g.target_amount:
            if g.status != "completed":
                g.status = "completed"
                db.session.commit()
        elif g.target_date < today:
            if g.status != "overdue":
                g.status = "overdue"
                db.session.commit()
        else:
            if g.status != "in_progress":
                g.status = "in_progress"
                db.session.commit()

    overall_pct = (float(total_saved) / float(total_target) * 100.0) if total_target > 0 else 0.0

    return render_template(
        "goals/goal_list.html",
        goals=goals,
        total_target=total_target,
        total_saved=total_saved,
        total_remaining=max(Decimal("0.00"), total_target - total_saved),
        overall_percentage=round(min(100.0, max(0.0, overall_pct)), 1),
    )


@goals_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_goal():
    """Create a new milestone financial savings goal."""
    form = FinancialGoalForm()

    if form.validate_on_submit():
        goal = FinancialGoal(
            user_id=current_user.id,
            title=form.title.data.strip(),
            target_amount=form.target_amount.data,
            current_amount=form.current_amount.data or Decimal("0.00"),
            target_date=form.target_date.data,
            notes=form.notes.data.strip() if form.notes.data else None,
            status="completed" if form.current_amount.data and form.current_amount.data >= form.target_amount.data else "in_progress",
        )
        db.session.add(goal)
        db.session.flush()  # Obtain goal.id

        # If opening balance was provided, record an initial contribution entry
        if form.current_amount.data and form.current_amount.data > Decimal("0.00"):
            initial_contrib = SavingsContribution(
                goal_id=goal.id,
                user_id=current_user.id,
                amount=form.current_amount.data,
                contribution_date=date.today(),
                notes="Initial opening balance",
            )
            db.session.add(initial_contrib)

        db.session.commit()
        flash(f"Financial goal '{goal.title}' created successfully!", "success")
        return redirect(url_for("goals.goal_detail", goal_id=goal.id))

    return render_template("goals/goal_form.html", form=form, action="Create")


@goals_bp.route("/<int:goal_id>", methods=["GET", "POST"])
@login_required
def goal_detail(goal_id: int):
    """View details of a goal, contribution history, and deposit savings."""
    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    contrib_form = SavingsContributionForm()

    contributions = (
        SavingsContribution.query.filter_by(goal_id=goal.id)
        .order_by(SavingsContribution.contribution_date.desc(), SavingsContribution.id.desc())
        .all()
    )

    return render_template(
        "goals/goal_detail.html",
        goal=goal,
        contributions=contributions,
        contrib_form=contrib_form,
    )


@goals_bp.route("/<int:goal_id>/contribute", methods=["POST"])
@login_required
def add_contribution(goal_id: int):
    """Record a savings contribution towards a goal."""
    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    form = SavingsContributionForm()

    if form.validate_on_submit():
        deposit_amount = form.amount.data
        contrib = SavingsContribution(
            goal_id=goal.id,
            user_id=current_user.id,
            amount=deposit_amount,
            contribution_date=form.contribution_date.data,
            notes=form.notes.data.strip() if form.notes.data else None,
        )
        db.session.add(contrib)

        # Update goal current amount
        goal.current_amount += deposit_amount

        # Check if goal reached 100%
        if goal.current_amount >= goal.target_amount:
            goal.status = "completed"
            notif = Notification(
                user_id=current_user.id,
                title=f"Goal Achieved: {goal.title}!",
                message=f"Congratulations! You reached your savings target of {current_user.currency}{goal.target_amount} for '{goal.title}'.",
                notification_type="success",
            )
            db.session.add(notif)
            flash(f"Hurray! You reached your savings target for '{goal.title}'! 🎉", "success")
        else:
            flash(f"Contribution of {current_user.currency}{deposit_amount} deposited successfully!", "success")

        db.session.commit()
        return redirect(url_for("goals.goal_detail", goal_id=goal.id))

    flash("Invalid contribution amount or details.", "danger")
    return redirect(url_for("goals.goal_detail", goal_id=goal.id))


@goals_bp.route("/<int:goal_id>/edit", methods=["GET", "POST"])
@login_required
def edit_goal(goal_id: int):
    """Edit goal parameters (title, target amount, target date, notes)."""
    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    form = FinancialGoalForm(obj=goal)

    if form.validate_on_submit():
        goal.title = form.title.data.strip()
        goal.target_amount = form.target_amount.data
        goal.target_date = form.target_date.data
        goal.notes = form.notes.data.strip() if form.notes.data else None

        if goal.current_amount >= goal.target_amount:
            goal.status = "completed"
        elif goal.target_date < date.today():
            goal.status = "overdue"
        else:
            goal.status = "in_progress"

        db.session.commit()
        flash("Financial goal updated successfully!", "success")
        return redirect(url_for("goals.goal_detail", goal_id=goal.id))

    return render_template("goals/goal_form.html", form=form, action="Edit", goal=goal)


@goals_bp.route("/<int:goal_id>/delete", methods=["POST"])
@login_required
def delete_goal(goal_id: int):
    """Delete a goal and its associated contributions."""
    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    db.session.delete(goal)
    db.session.commit()

    flash(f"Goal '{goal.title}' deleted successfully.", "info")
    return redirect(url_for("goals.index"))
