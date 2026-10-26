from datetime import datetime, timezone
from app.extensions import db


class Transaction(db.Model):
    """
    Transaction model recording every financial movement (income or expense).
    Uses high-precision DECIMAL for exact financial accounting.
    """
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    payment_method = db.Column(db.String(50), nullable=False)  # Cash, UPI, Credit Card, Debit Card, Net Banking
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.Index("ix_transactions_user_date", "user_id", "transaction_date"),
        db.Index("ix_transactions_user_type_date", "user_id", "transaction_type", "transaction_date"),
    )

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type='{self.transaction_type}' amount={self.amount} date={self.transaction_date}>"
