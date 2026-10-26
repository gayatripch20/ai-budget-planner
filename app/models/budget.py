from datetime import datetime, timezone
from app.extensions import db


class Budget(db.Model):
    """
    Monthly category budget cap set by a user.
    Prevents duplicate budgets for the same category in the same month/year.
    """
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False)  # 1 to 12
    year = db.Column(db.Integer, nullable=False)   # e.g. 2026
    amount_limit = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "category_id", "month", "year", name="uq_user_category_month_year"),
    )

    def __repr__(self) -> str:
        return f"<Budget id={self.id} user={self.user_id} cat={self.category_id} {self.month}/{self.year} limit={self.amount_limit}>"
