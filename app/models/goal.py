from datetime import datetime, date, timezone
from decimal import Decimal
from app.extensions import db


class FinancialGoal(db.Model):
    """
    FinancialGoal model representing milestone savings targets (e.g., Laptop, Emergency Fund).
    Includes dynamic properties for progress percentage and amortization formulas.
    """
    __tablename__ = "financial_goals"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)
    current_amount = db.Column(db.Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="in_progress", nullable=False)  # in_progress, completed, overdue
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    contributions = db.relationship(
        "SavingsContribution",
        backref="goal",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    @property
    def remaining_amount(self) -> Decimal:
        """Calculate the remaining amount to reach the target."""
        rem = Decimal(str(self.target_amount)) - Decimal(str(self.current_amount))
        return max(Decimal("0.00"), rem)

    @property
    def percentage_completed(self) -> float:
        """Calculate the completion percentage capped at 100%."""
        if not self.target_amount or Decimal(str(self.target_amount)) <= 0:
            return 0.0
        pct = (float(self.current_amount) / float(self.target_amount)) * 100.0
        return round(min(100.0, max(0.0, pct)), 2)

    @property
    def months_remaining(self) -> int:
        """Calculate months remaining until the target date."""
        today = date.today()
        if self.target_date <= today:
            return 0
        diff_years = self.target_date.year - today.year
        diff_months = self.target_date.month - today.month
        total_months = (diff_years * 12) + diff_months
        # If target day is earlier in the month, count at least 1 month if in future
        return max(1, total_months)

    @property
    def required_monthly_savings(self) -> Decimal:
        """
        Amortization calculation:
        Required Monthly Contribution = Remaining Amount / Months Remaining
        """
        rem = self.remaining_amount
        if rem <= Decimal("0.00"):
            return Decimal("0.00")
        months = self.months_remaining
        if months <= 0:
            return rem  # Due immediately
        monthly = rem / Decimal(str(months))
        return round(monthly, 2)

    def __repr__(self) -> str:
        return f"<FinancialGoal id={self.id} title='{self.title}' target={self.target_amount}>"


class SavingsContribution(db.Model):
    """
    Individual contribution allocated toward a specific financial goal.
    """
    __tablename__ = "savings_contributions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    goal_id = db.Column(db.Integer, db.ForeignKey("financial_goals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    contribution_date = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<SavingsContribution id={self.id} goal_id={self.goal_id} amount={self.amount}>"
