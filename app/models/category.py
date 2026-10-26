from datetime import datetime, timezone
from app.extensions import db


class Category(db.Model):
    """
    Category model for categorizing transactions and setting budgets.
    Supports system-wide default categories (user_id is None) and user-defined custom categories.
    """
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    icon = db.Column(db.String(50), default="bi-tag", nullable=False)  # Bootstrap icon class
    color = db.Column(db.String(20), default="#4e73df", nullable=False)  # HEX color code
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    transactions = db.relationship("Transaction", backref="category", lazy="dynamic")
    budgets = db.relationship("Budget", backref="category", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name='{self.name}' type='{self.type}'>"
