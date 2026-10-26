from datetime import date
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy import func, extract
from app.extensions import db
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import FinancialGoal
from app.models.category import Category
from app.services.analytics import get_monthly_summary


# Standard Classification of Categories for the 50/30/20 Rule
NEEDS_CATEGORIES = {"Rent & Housing", "Groceries", "Utilities & Bills", "Healthcare & Medical", "Education & Courses"}
WANTS_CATEGORIES = {"Food & Dining", "Shopping & Gadgets", "Entertainment", "Travel & Transport", "Miscellaneous"}


def generate_smart_recommendations(user_id: int, year: int, month: int, forecast_amount: float = 0.0) -> Dict[str, Any]:
    """
    Generate transparent, traceable personal finance recommendations
    grounded in established economic guidelines (50/30/20 rule, budget velocity, goal feasibility).
    """
    recommendations = []
    summary = get_monthly_summary(user_id, year, month)
    income = float(summary["income"])
    expenses = float(summary["expenses"])
    net_savings = float(summary["net_savings"])

    # -------------------------------------------------------------------------
    # RULE 1: 50/30/20 BUDGET RULE ANALYSIS
    # -------------------------------------------------------------------------
    needs_spent = 0.0
    wants_spent = 0.0

    tx_by_cat = (
        db.session.query(Category.name, func.coalesce(func.sum(Transaction.amount), 0))
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        )
        .group_by(Category.name)
        .all()
    )

    for cat_name, amt in tx_by_cat:
        amt_f = float(amt)
        if cat_name in NEEDS_CATEGORIES:
            needs_spent += amt_f
        else:
            wants_spent += amt_f

    needs_pct = round((needs_spent / income * 100.0), 1) if income > 0 else 0.0
    wants_pct = round((wants_spent / income * 100.0), 1) if income > 0 else 0.0
    savings_pct = round((max(0.0, net_savings) / income * 100.0), 1) if income > 0 else 0.0

    rule_50_30_20 = {
        "needs_spent": needs_spent,
        "needs_pct": needs_pct,
        "wants_spent": wants_spent,
        "wants_pct": wants_pct,
        "savings_pct": savings_pct,
    }

    if income > 0:
        if wants_pct > 35.0:
            excess_wants = wants_spent - (income * 0.30)
            recommendations.append({
                "type": "warning",
                "badge": "50/30/20 Rule",
                "title": "Discretionary Spending Exceeds Target",
                "message": (
                    f"Your discretionary spending ('Wants') currently represents {wants_pct}% of your income "
                    f"(target: 30%). Trimming discretionary purchases by ₹{excess_wants:,.2f} will balance your cash flow."
                ),
                "action": "Review Entertainment & Dining",
            })
        elif savings_pct < 20.0 and net_savings >= 0:
            shortfall = (income * 0.20) - net_savings
            recommendations.append({
                "type": "info",
                "badge": "Savings Benchmark",
                "title": "Boost Monthly Savings towards 20%",
                "message": (
                    f"Your current savings rate is {savings_pct}% (recommended benchmark: 20%). "
                    f"Saving an additional ₹{shortfall:,.2f} this month will secure your emergency cushion."
                ),
                "action": "Increase Goal Allocation",
            })

    # -------------------------------------------------------------------------
    # RULE 2: CATEGORY BUDGET BREACHES
    # -------------------------------------------------------------------------
    budgets = Budget.query.filter_by(user_id=user_id, month=month, year=year).all()
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
        spent_f = float(spent or 0.0)
        limit_f = float(b.amount_limit)

        if spent_f >= limit_f:
            recommendations.append({
                "type": "danger",
                "badge": "Budget Breach",
                "title": f"Limit Exceeded: {b.category.name}",
                "message": f"You spent ₹{spent_f:,.2f} against a limit of ₹{limit_f:,.2f}. Freeze spending in this category.",
                "action": "Freeze Category Outflow",
            })
        elif spent_f >= limit_f * 0.80:
            recommendations.append({
                "type": "warning",
                "badge": "Budget Warning",
                "title": f"Approaching Cap: {b.category.name}",
                "message": f"You have reached {round(spent_f / limit_f * 100)}% of your limit. Only ₹{(limit_f - spent_f):,.2f} remains.",
                "action": "Pace Expenses",
            })

    # -------------------------------------------------------------------------
    # RULE 3: FINANCIAL GOALS FEASIBILITY
    # -------------------------------------------------------------------------
    active_goals = FinancialGoal.query.filter_by(user_id=user_id, status="in_progress").all()
    total_required_monthly = sum(float(g.required_monthly_savings) for g in active_goals)

    if active_goals and total_required_monthly > 0:
        if net_savings < total_required_monthly:
            deficit = total_required_monthly - net_savings
            recommendations.append({
                "type": "warning",
                "badge": "Goal Feasibility",
                "title": "Projected Goal Savings Deficit",
                "message": (
                    f"Your active goals require ₹{total_required_monthly:,.2f}/mo in total contributions, "
                    f"but current surplus is ₹{max(0.0, net_savings):,.2f}. "
                    f"A deficit of ₹{deficit:,.2f} may delay your target deadlines."
                ),
                "action": "Prioritize Top Goal",
            })
        else:
            recommendations.append({
                "type": "success",
                "badge": "Goal On-Track",
                "title": "Goal Milestones Fully Funded",
                "message": (
                    f"Your current surplus of ₹{net_savings:,.2f} comfortably covers your total "
                    f"monthly goal commitments of ₹{total_required_monthly:,.2f}."
                ),
                "action": "Deposit Contributions",
            })

    # -------------------------------------------------------------------------
    # RULE 4: PREDICTIVE FORECAST RISK ALERT
    # -------------------------------------------------------------------------
    total_budget_limit = sum(float(b.amount_limit) for b in budgets) if budgets else 0.0
    if forecast_amount > 0 and total_budget_limit > 0 and forecast_amount > total_budget_limit:
        over_pred = forecast_amount - total_budget_limit
        recommendations.append({
            "type": "danger",
            "badge": "AI Forecast Alert",
            "title": "Upcoming Expense Forecast Exceeds Budget",
            "message": (
                f"Our ML model projects upcoming expenses of ₹{forecast_amount:,.2f}, which exceeds your "
                f"monthly planned budget of ₹{total_budget_limit:,.2f} by ₹{over_pred:,.2f}. Adjust spending early."
            ),
            "action": "Review Planned Budgets",
        })

    # Fallback greeting recommendation if user has no entries yet
    if not recommendations:
        recommendations.append({
            "type": "info",
            "badge": "Getting Started",
            "title": "Financial Health On Track",
            "message": "Continue logging daily transactions and setting monthly budgets to receive tailored AI insights.",
            "action": "Log Today's Expenses",
        })

    return {
        "rule_50_30_20": rule_50_30_20,
        "recommendations": recommendations,
    }
