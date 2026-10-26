"""
Automated Test Suite for Dashboard and Analytics Engine.
Validates financial metric calculations, savings rate formulas, MoM variance,
Chart.js data transformations, notification management, and data isolation.
"""
from datetime import date
from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.notification import Notification
from app.services.analytics import (
    get_monthly_summary,
    get_category_spending_breakdown,
    get_six_month_trend,
    get_budget_performance,
    get_mom_expense_variance,
)


@pytest.fixture
def app():
    """Create test application context configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()

        # Seed categories
        salary_cat = Category(name="Salary", type="income", icon="bi-cash", color="#1cc88a", is_default=True)
        food_cat = Category(name="Food & Dining", type="expense", icon="bi-cup", color="#e74a3b", is_default=True)
        travel_cat = Category(name="Travel", type="expense", icon="bi-car", color="#0dcaf0", is_default=True)
        db.session.add_all([salary_cat, food_cat, travel_cat])

        # Seed User A
        user_a = User(full_name="User Alpha", email="alpha@example.com")
        user_a.set_password("AlphaPass123!")
        db.session.add(user_a)

        # Seed User B
        user_b = User(full_name="User Beta", email="beta@example.com")
        user_b.set_password("BetaPass123!")
        db.session.add(user_b)

        db.session.commit()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_user(client, email, password):
    """Helper to log in a user."""
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def test_monthly_summary_and_savings_rate(app):
    """Verify calculation of income, expenses, net balance, and savings rate percentage."""
    user = User.query.filter_by(email="alpha@example.com").first()
    salary_cat = Category.query.filter_by(name="Salary").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()
    today = date.today()

    # Income = 50,000, Expense = 20,000 -> Net = 30,000, Savings Rate = 60.0%
    inc = Transaction(user_id=user.id, category_id=salary_cat.id, transaction_type="income", amount=Decimal("50000.00"), transaction_date=today, payment_method="Net Banking")
    exp = Transaction(user_id=user.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal("20000.00"), transaction_date=today, payment_method="UPI")
    db.session.add_all([inc, exp])
    db.session.commit()

    summary = get_monthly_summary(user.id, today.year, today.month)
    assert summary["income"] == Decimal("50000.00")
    assert summary["expenses"] == Decimal("20000.00")
    assert summary["net_savings"] == Decimal("30000.00")
    assert summary["savings_rate"] == 60.0


def test_category_breakdown_and_mom_variance(app):
    """Verify category breakdown aggregations and Month-over-Month variance computation."""
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()
    travel_cat = Category.query.filter_by(name="Travel").first()
    today = date.today()

    # Expenses in current month
    tx1 = Transaction(user_id=user.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal("3000.00"), transaction_date=today, payment_method="UPI")
    tx2 = Transaction(user_id=user.id, category_id=travel_cat.id, transaction_type="expense", amount=Decimal("1000.00"), transaction_date=today, payment_method="Cash")
    db.session.add_all([tx1, tx2])
    db.session.commit()

    breakdown = get_category_spending_breakdown(user.id, today.year, today.month)
    assert "Food & Dining" in breakdown["labels"]
    assert "Travel" in breakdown["labels"]
    assert breakdown["total_spent"] == Decimal("4000.00")

    # Food was 3,000 of 4,000 = 75.0%
    food_item = next(c for c in breakdown["categories"] if c["name"] == "Food & Dining")
    assert food_item["percentage"] == 75.0

    # Test MoM variance
    mom = get_mom_expense_variance(user.id, today.year, today.month)
    assert mom["current_expenses"] == Decimal("4000.00")


def test_six_month_trend(app):
    """Verify that 6 month trend service returns 6 historical labels and numerical lists."""
    user = User.query.filter_by(email="alpha@example.com").first()
    trend = get_six_month_trend(user.id)
    assert len(trend["labels"]) == 6
    assert len(trend["income"]) == 6
    assert len(trend["expenses"]) == 6


def test_dashboard_and_analytics_views(client):
    """Verify HTTP responses for dashboard and analytics views."""
    login_user(client, "alpha@example.com", "AlphaPass123!")

    dash_res = client.get("/dashboard/")
    assert dash_res.status_code == 200
    assert b"Financial Dashboard" in dash_res.data

    analytics_res = client.get("/analytics/")
    assert analytics_res.status_code == 200
    assert b"Financial Analytics" in analytics_res.data


def test_notification_management(client):
    """Verify marking notifications as read."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    user = User.query.filter_by(email="alpha@example.com").first()

    notif = Notification(user_id=user.id, title="Test Alert", message="Something happened", notification_type="warning")
    db.session.add(notif)
    db.session.commit()

    # Mark as read
    res = client.post(f"/dashboard/notifications/{notif.id}/read", follow_redirects=True)
    assert res.status_code == 200

    updated_notif = db.session.get(Notification, notif.id)
    assert updated_notif.is_read is True


def test_cross_user_analytics_isolation(client):
    """
    CRITICAL SECURITY TEST:
    Verify that User Beta cannot see User Alpha's financial stats on their dashboard.
    """
    user_a = User.query.filter_by(email="alpha@example.com").first()
    salary_cat = Category.query.filter_by(name="Salary").first()

    # User Alpha has 100,000 salary
    tx_a = Transaction(user_id=user_a.id, category_id=salary_cat.id, transaction_type="income", amount=Decimal("100000.00"), transaction_date=date.today(), payment_method="Net Banking")
    db.session.add(tx_a)
    db.session.commit()

    # Log in as User Beta (who has 0 income)
    login_user(client, "beta@example.com", "BetaPass123!")
    res = client.get("/dashboard/")
    assert res.status_code == 200
    assert b"100000.00" not in res.data
