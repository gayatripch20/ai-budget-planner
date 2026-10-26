"""
Centralized database models package.
Exposes all SQLAlchemy models for convenient, consistent imports across the application.
"""
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import FinancialGoal, SavingsContribution
from app.models.notification import Notification
from app.models.prediction import ExpensePrediction

__all__ = [
    "User",
    "Category",
    "Transaction",
    "Budget",
    "FinancialGoal",
    "SavingsContribution",
    "Notification",
    "ExpensePrediction",
]
