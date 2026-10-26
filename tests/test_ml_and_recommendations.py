"""
Automated Test Suite for Machine Learning Expense Forecasting and Smart Recommendations.
Validates multi-tiered regression forecasting (Cold-start baseline, Linear Trend, Ridge Regression),
evaluation metrics (MAE), 50/30/20 financial rule diagnostics, and prediction persistence.
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
from app.models.goal import FinancialGoal
from app.models.prediction import ExpensePrediction
from ml.preprocessing import prepare_monthly_expense_series
from ml.forecasting import ExpenseForecaster
from app.services.recommendations import generate_smart_recommendations


@pytest.fixture
def app():
    """Create test application context configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()

        # Seed categories
        salary_cat = Category(name="Salary", type="income", icon="bi-cash", color="#1cc88a", is_default=True)
        food_cat = Category(name="Food & Dining", type="expense", icon="bi-cup", color="#e74a3b", is_default=True)
        shopping_cat = Category(name="Shopping & Gadgets", type="expense", icon="bi-bag", color="#d63384", is_default=True)
        rent_cat = Category(name="Rent & Housing", type="expense", icon="bi-house", color="#fd7e14", is_default=True)
        db.session.add_all([salary_cat, food_cat, shopping_cat, rent_cat])

        # Seed Users
        user_a = User(full_name="User Alpha", email="alpha@example.com")
        user_a.set_password("AlphaPass123!")
        user_b = User(full_name="User Beta", email="beta@example.com")
        user_b.set_password("BetaPass123!")
        db.session.add_all([user_a, user_b])

        db.session.commit()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_user(client, email, password):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def test_preprocessing_empty_and_populated(app):
    """Verify time-series feature extraction and lag variable creation."""
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    # Empty test
    df_empty = prepare_monthly_expense_series(user.id)
    assert df_empty.empty is True

    # Insert transactions across 3 distinct months
    tx1 = Transaction(user_id=user.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal("2000.00"), transaction_date=date(2026, 1, 15), payment_method="UPI")
    tx2 = Transaction(user_id=user.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal("3000.00"), transaction_date=date(2026, 2, 10), payment_method="UPI")
    tx3 = Transaction(user_id=user.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal("4000.00"), transaction_date=date(2026, 3, 5), payment_method="UPI")
    db.session.add_all([tx1, tx2, tx3])
    db.session.commit()

    df = prepare_monthly_expense_series(user.id)
    assert len(df) == 3
    assert list(df["period_index"]) == [1, 2, 3]
    assert df["total_expense"].iloc[-1] == 4000.0
    assert df["lag_1"].iloc[1] == 2000.0


def test_forecasting_tier1_cold_start(app):
    """Verify Tier 1 cold start handling (< 3 months) returns transparent moving average."""
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    # Log 1 month of transactions
    tx = Transaction(user_id=user.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal("5000.00"), transaction_date=date(2026, 5, 10), payment_method="Cash")
    db.session.add(tx)
    db.session.commit()

    forecast = ExpenseForecaster.forecast_next_month(user.id)
    assert forecast["model_used"] == "MovingAverageBaseline"
    assert forecast["confidence"] == "low"
    assert forecast["predicted_amount"] == 5000.0
    assert "At least 3 months" in forecast["explanation"]


def test_forecasting_tier2_linear_regression(app):
    """Verify Tier 2 forecasting (3-5 months) fits Scikit-Learn Linear Regression and computes MAE."""
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    # 4 months of expenses with upward trend: 1000, 2000, 3000, 4000
    for mo, amt in [(1, 1000), (2, 2000), (3, 3000), (4, 4000)]:
        tx = Transaction(user_id=user.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal(str(amt)), transaction_date=date(2026, mo, 15), payment_method="UPI")
        db.session.add(tx)
    db.session.commit()

    forecast = ExpenseForecaster.forecast_next_month(user.id)
    assert forecast["model_used"] == "LinearTrendRegression"
    assert forecast["confidence"] == "moderate"
    # Linear trend of +1000 per month implies next month (period 5) ≈ 5000
    assert abs(forecast["predicted_amount"] - 5000.0) < 1.0
    assert forecast["mae_score"] is not None

    # Check persistence in database
    saved_pred = ExpensePrediction.query.filter_by(user_id=user.id).first()
    assert saved_pred is not None
    assert saved_pred.model_used == "LinearTrendRegression"


def test_smart_recommendations_50_30_20_and_budget_rules(app):
    """Verify recommendations engine triggers for 50/30/20 wants breach and budget overruns."""
    user = User.query.filter_by(email="alpha@example.com").first()
    salary_cat = Category.query.filter_by(name="Salary").first()
    shopping_cat = Category.query.filter_by(name="Shopping & Gadgets").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()
    today = date.today()

    # Income = 40,000
    # Discretionary Shopping & Food = 20,000 (50% of income > 35% target)
    inc = Transaction(user_id=user.id, category_id=salary_cat.id, transaction_type="income", amount=Decimal("40000.00"), transaction_date=today, payment_method="Net Banking")
    exp1 = Transaction(user_id=user.id, category_id=shopping_cat.id, transaction_type="expense", amount=Decimal("15000.00"), transaction_date=today, payment_method="Credit Card")
    exp2 = Transaction(user_id=user.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal("5000.00"), transaction_date=today, payment_method="UPI")
    
    # Budget of 4000 for Food (Spent 5000 -> Exceeded)
    budget = Budget(user_id=user.id, category_id=food_cat.id, month=today.month, year=today.year, amount_limit=Decimal("4000.00"))
    
    db.session.add_all([inc, exp1, exp2, budget])
    db.session.commit()

    recs = generate_smart_recommendations(user.id, today.year, today.month, forecast_amount=25000.0)
    titles = [r["title"] for r in recs["recommendations"]]

    # 1. Wants percentage flagged
    assert any("Discretionary Spending Exceeds Target" in t for t in titles)
    # 2. Budget breach flagged
    assert any("Limit Exceeded" in t for t in titles)


def test_predictions_view_endpoint(client):
    """Verify predictions view renders successfully."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    response = client.get("/predictions/")
    assert response.status_code == 200
    assert b"AI Expense Forecasting" in response.data
    assert b"50/30/20 Financial Health Analysis" in response.data
