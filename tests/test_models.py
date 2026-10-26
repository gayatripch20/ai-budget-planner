"""
Unit Tests for Database Models.
Validates model constraints, relationships, password security, and financial amortization calculations.
Uses in-memory SQLite (TestingConfig) for fast, isolated automated testing.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db
from app.models import (
    User,
    Category,
    Transaction,
    Budget,
    FinancialGoal,
    SavingsContribution,
    Notification,
    ExpensePrediction,
)


@pytest.fixture
def app():
    """Create test application context with in-memory database."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


def test_user_password_hashing(app):
    """Verify that passwords are securely hashed and checked."""
    user = User(full_name="Pooja Sharma", email="pooja@example.com")
    user.set_password("SecurePass123!")

    assert user.password_hash != "SecurePass123!"
    assert user.check_password("SecurePass123!") is True
    assert user.check_password("WrongPassword") is False


def test_user_persistence_and_defaults(app):
    """Verify user creation and default currency."""
    user = User(full_name="Rahul Verma", email="rahul@example.com")
    user.set_password("MyPass99")
    db.session.add(user)
    db.session.commit()

    saved_user = User.query.filter_by(email="rahul@example.com").first()
    assert saved_user is not None
    assert saved_user.currency == "₹"
    assert saved_user.id is not None


def test_category_and_transactions(app):
    """Verify category creation and transaction logging with exact decimal precision."""
    user = User(full_name="Anita Roy", email="anita@example.com")
    user.set_password("Pass123")
    db.session.add(user)
    db.session.commit()

    cat = Category(name="Groceries", type="expense", icon="bi-cart", color="#20c997", is_default=True)
    db.session.add(cat)
    db.session.commit()

    tx = Transaction(
        user_id=user.id,
        category_id=cat.id,
        transaction_type="expense",
        amount=Decimal("1450.75"),
        transaction_date=date.today(),
        payment_method="UPI",
        description="Weekly vegetables and staples",
    )
    db.session.add(tx)
    db.session.commit()

    saved_tx = Transaction.query.filter_by(user_id=user.id).first()
    assert saved_tx is not None
    assert saved_tx.amount == Decimal("1450.75")
    assert saved_tx.category.name == "Groceries"
    assert saved_tx.user.full_name == "Anita Roy"


def test_budget_creation(app):
    """Verify budget limits per user and category."""
    user = User(full_name="Karan Dave", email="karan@example.com")
    user.set_password("Pass123")
    db.session.add(user)
    cat = Category(name="Food", type="expense")
    db.session.add(cat)
    db.session.commit()

    budget = Budget(
        user_id=user.id,
        category_id=cat.id,
        month=10,
        year=2026,
        amount_limit=Decimal("8000.00"),
    )
    db.session.add(budget)
    db.session.commit()

    saved_budget = Budget.query.filter_by(user_id=user.id, month=10, year=2026).first()
    assert saved_budget is not None
    assert saved_budget.amount_limit == Decimal("8000.00")


def test_financial_goal_calculations(app):
    """
    Verify mathematical calculations for financial goals:
    - Remaining amount
    - Percentage completed
    - Required monthly savings amortization formula
    """
    user = User(full_name="Meera Sen", email="meera@example.com")
    user.set_password("Pass123")
    db.session.add(user)
    db.session.commit()

    # Target date 4 months from now
    target_date = date.today() + timedelta(days=120)

    goal = FinancialGoal(
        user_id=user.id,
        title="New MacBook",
        target_amount=Decimal("100000.00"),
        current_amount=Decimal("25000.00"),
        target_date=target_date,
    )
    db.session.add(goal)
    db.session.commit()

    # Remaining = 100,000 - 25,000 = 75,000
    assert goal.remaining_amount == Decimal("75000.00")
    # Percentage = 25%
    assert goal.percentage_completed == 25.0
    # Required monthly = 75,000 / months_remaining
    assert goal.months_remaining >= 3
    expected_monthly = round(Decimal("75000.00") / Decimal(str(goal.months_remaining)), 2)
    assert goal.required_monthly_savings == expected_monthly

    # Add a contribution
    contrib = SavingsContribution(
        goal_id=goal.id,
        user_id=user.id,
        amount=Decimal("15000.00"),
        contribution_date=date.today(),
        notes="Diwali bonus deposit",
    )
    db.session.add(contrib)
    goal.current_amount += Decimal("15000.00")
    db.session.commit()

    assert goal.current_amount == Decimal("40000.00")
    assert goal.percentage_completed == 40.0
    assert goal.remaining_amount == Decimal("60000.00")


def test_notification_and_prediction(app):
    """Verify in-app notification logging and prediction storage."""
    user = User(full_name="Vikram Singh", email="vikram@example.com")
    user.set_password("Pass123")
    db.session.add(user)
    db.session.commit()

    notif = Notification(
        user_id=user.id,
        title="Budget Alert",
        message="Food category reached 85% of monthly limit.",
        notification_type="warning",
    )
    pred = ExpensePrediction(
        user_id=user.id,
        forecast_month=11,
        forecast_year=2026,
        predicted_amount=Decimal("22500.00"),
        model_used="LinearRegression",
        mae_score=Decimal("340.50"),
    )
    db.session.add_all([notif, pred])
    db.session.commit()

    assert Notification.query.filter_by(user_id=user.id, is_read=False).count() == 1
    assert ExpensePrediction.query.filter_by(user_id=user.id).first().predicted_amount == Decimal("22500.00")
