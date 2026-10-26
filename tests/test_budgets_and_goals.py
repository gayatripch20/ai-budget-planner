"""
Automated Test Suite for Monthly Budget Planning and Financial Goals Management.
Validates budget utilization, overspending notifications, amortization formulas,
deposit contributions, and multi-tenant isolation.
"""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import FinancialGoal, SavingsContribution
from app.models.notification import Notification


@pytest.fixture
def app():
    """Create test application context configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()

        # Seed category
        food_cat = Category(name="Food & Dining", type="expense", icon="bi-cup", color="#e74a3b", is_default=True)
        db.session.add(food_cat)

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


def test_budget_creation_and_utilization(client):
    """Verify creating a budget and computing utilization percentage against actual spending."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()
    today = date.today()

    # 1. Create a budget of 5000 for current month
    response = client.post(
        "/budgets/new",
        data={
            "category_id": food_cat.id,
            "month": today.month,
            "year": today.year,
            "amount_limit": "5000.00",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Budget created successfully!" in response.data

    # 2. Add an expense of 4200 (84% of budget -> triggers warning alert)
    tx = Transaction(
        user_id=user.id,
        category_id=food_cat.id,
        transaction_type="expense",
        amount=Decimal("4200.00"),
        transaction_date=today,
        payment_method="UPI",
    )
    db.session.add(tx)
    db.session.commit()

    # 3. View budget planner index
    res = client.get(f"/budgets/?month={today.month}&year={today.year}")
    assert res.status_code == 200
    assert b"84.0%" in res.data or b"84%" in res.data
    assert b"Near Limit" in res.data

    # Verify that a warning notification was created
    notif = Notification.query.filter_by(user_id=user.id, notification_type="warning").first()
    assert notif is not None
    assert "Budget Warning" in notif.title


def test_budget_overrun_alert(client):
    """Verify danger alert when spending exceeds 100% of budget."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()
    today = date.today()

    # Budget of 2000
    budget = Budget(
        user_id=user.id,
        category_id=food_cat.id,
        month=today.month,
        year=today.year,
        amount_limit=Decimal("2000.00"),
    )
    # Expense of 2500 (125%)
    tx = Transaction(
        user_id=user.id,
        category_id=food_cat.id,
        transaction_type="expense",
        amount=Decimal("2500.00"),
        transaction_date=today,
        payment_method="Cash",
    )
    db.session.add_all([budget, tx])
    db.session.commit()

    res = client.get(f"/budgets/?month={today.month}&year={today.year}")
    assert res.status_code == 200
    assert b"Exceeded" in res.data

    notif = Notification.query.filter_by(user_id=user.id, notification_type="danger").first()
    assert notif is not None
    assert "Exceeded!" in notif.title


def test_goal_creation_and_amortization(client):
    """Verify goal creation, percentage completion, and required monthly savings."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    target_date = date.today() + timedelta(days=120)

    response = client.post(
        "/goals/new",
        data={
            "title": "Emergency Fund",
            "target_amount": "60000.00",
            "current_amount": "15000.00",
            "target_date": target_date.isoformat(),
            "notes": "6 months of living expenses",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Emergency Fund" in response.data

    user = User.query.filter_by(email="alpha@example.com").first()
    goal = FinancialGoal.query.filter_by(user_id=user.id, title="Emergency Fund").first()
    assert goal is not None
    assert goal.percentage_completed == 25.0
    assert goal.remaining_amount == Decimal("45000.00")
    assert goal.required_monthly_savings > Decimal("0.00")


def test_goal_contribution_and_completion(client):
    """Verify adding a deposit contribution reaches 100% completion and triggers notification."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    user = User.query.filter_by(email="alpha@example.com").first()

    # Goal target = 10,000, current = 8,000
    goal = FinancialGoal(
        user_id=user.id,
        title="Laptop Upgrade",
        target_amount=Decimal("10000.00"),
        current_amount=Decimal("8000.00"),
        target_date=date.today() + timedelta(days=90),
    )
    db.session.add(goal)
    db.session.commit()

    # Deposit contribution of 2,500 (brings total to 10,500 >= 10,000)
    response = client.post(
        f"/goals/{goal.id}/contribute",
        data={
            "amount": "2500.00",
            "contribution_date": date.today().isoformat(),
            "notes": "Freelance project payment",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Target Achieved!" in response.data or b"Hurray" in response.data

    updated_goal = db.session.get(FinancialGoal, goal.id)
    assert updated_goal.current_amount == Decimal("10500.00")
    assert updated_goal.status == "completed"

    notif = Notification.query.filter_by(user_id=user.id, notification_type="success").first()
    assert notif is not None
    assert "Goal Achieved" in notif.title


def test_cross_user_isolation_budgets_and_goals(client):
    """
    CRITICAL SECURITY TEST:
    Verify that User Beta cannot edit or delete User Alpha's budget or goal.
    """
    user_a = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    budget_a = Budget(
        user_id=user_a.id,
        category_id=food_cat.id,
        month=10,
        year=2026,
        amount_limit=Decimal("5000.00"),
    )
    goal_a = FinancialGoal(
        user_id=user_a.id,
        title="Alpha Secret Goal",
        target_amount=Decimal("50000.00"),
        current_amount=Decimal("10000.00"),
        target_date=date.today() + timedelta(days=60),
    )
    db.session.add_all([budget_a, goal_a])
    db.session.commit()

    # Log in as User Beta
    login_user(client, "beta@example.com", "BetaPass123!")

    # Attempt to edit User Alpha's budget
    assert client.get(f"/budgets/{budget_a.id}/edit").status_code == 404
    # Attempt to delete User Alpha's budget
    assert client.post(f"/budgets/{budget_a.id}/delete").status_code == 404

    # Attempt to view User Alpha's goal detail
    assert client.get(f"/goals/{goal_a.id}").status_code == 404
    # Attempt to edit User Alpha's goal
    assert client.get(f"/goals/{goal_a.id}/edit").status_code == 404
    # Attempt to delete User Alpha's goal
    assert client.post(f"/goals/{goal_a.id}/delete").status_code == 404
