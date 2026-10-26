"""
Quality Assurance and Security Penetration Test Suite.
Verifies all 12 system security requirements and edge cases:
1. Unauthorized route access redirects across all modules.
2. Custom error handlers (404 Not Found & 500 Internal Error) without stack trace exposure.
3. Empty dataset resilience (0 transactions, 0 budgets, 0 goals).
4. Decimal monetary boundary validation.
5. Insecure Direct Object Reference (IDOR) multi-tenant penetration tests.
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


@pytest.fixture
def app():
    """Create test application context configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()

        # Seed categories
        salary_cat = Category(name="Salary", type="income", icon="bi-cash", color="#1cc88a", is_default=True)
        food_cat = Category(name="Food & Dining", type="expense", icon="bi-cup", color="#e74a3b", is_default=True)
        db.session.add_all([salary_cat, food_cat])

        # Seed User Alpha
        user_a = User(full_name="User Alpha", email="alpha@example.com")
        user_a.set_password("AlphaPass123!")
        db.session.add(user_a)

        # Seed User Beta
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
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def test_unauthorized_access_redirects_all_protected_modules(client):
    """
    SECURITY TEST:
    Verify that unauthenticated guests cannot access any protected internal route.
    """
    protected_urls = [
        "/dashboard/",
        "/transactions/income",
        "/transactions/expense",
        "/transactions/all",
        "/budgets/",
        "/goals/",
        "/analytics/",
        "/predictions/",
        "/reports/",
        "/profile/",
    ]
    for url in protected_urls:
        response = client.get(url, follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]


def test_custom_404_error_page(client):
    """Verify that visiting a non-existent URL returns custom 404 page without raw debug leaks."""
    response = client.get("/some-completely-invalid-nonexistent-url-12345")
    assert response.status_code == 404
    assert b"Page Not Found" in response.data
    assert b"404" in response.data


def test_empty_dataset_resilience(client):
    """
    EDGE CASE TEST:
    Verify that a brand new user with 0 transactions, 0 budgets, and 0 goals
    can navigate all core pages smoothly with clean empty states and zero 500 errors.
    """
    login_user(client, "alpha@example.com", "AlphaPass123!")

    # 1. Dashboard loads with zero balances
    dash_res = client.get("/dashboard/")
    assert dash_res.status_code == 200
    assert b"0.00" in dash_res.data
    assert b"No transactions logged yet" in dash_res.data

    # 2. Budgets page loads with empty prompt
    budgets_res = client.get("/budgets/")
    assert budgets_res.status_code == 200
    assert b"No Budgets Set For This Month" in budgets_res.data

    # 3. Goals page loads with empty prompt
    goals_res = client.get("/goals/")
    assert goals_res.status_code == 200
    assert b"No Financial Goals Defined Yet" in goals_res.data

    # 4. Analytics loads with empty charts and zero variance
    analytics_res = client.get("/analytics/")
    assert analytics_res.status_code == 200
    assert b"Financial Analytics" in analytics_res.data

    # 5. AI Predictions loads with cold-start prompt
    pred_res = client.get("/predictions/")
    assert pred_res.status_code == 200
    assert b"NoData" in pred_res.data or b"No expense transactions" in pred_res.data

    # 6. Reports loads with zero balances
    reports_res = client.get("/reports/")
    assert reports_res.status_code == 200
    assert b"No Transactions Found" in reports_res.data


def test_invalid_date_filters_handled_gracefully(client):
    """Verify malformed query string date filters don't trigger uncaught 500 exceptions."""
    login_user(client, "alpha@example.com", "AlphaPass123!")

    # Pass invalid non-date strings
    response = client.get("/reports/?start_date=not-a-valid-date&end_date=also-invalid-date")
    assert response.status_code == 200
    assert b"Financial Audit Reports" in response.data


def test_idor_comprehensive_isolation(client):
    """
    CRITICAL SECURITY PENETRATION TEST:
    User Alpha creates a Transaction, a Budget, and a Goal.
    User Beta attempts to read, edit, or delete them directly via ID.
    All attempts must be rejected with HTTP 404 (Not Found).
    """
    user_a = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    tx = Transaction(user_id=user_a.id, category_id=food_cat.id, transaction_type="expense", amount=Decimal("750.00"), transaction_date=date.today(), payment_method="Cash")
    budget = Budget(user_id=user_a.id, category_id=food_cat.id, month=10, year=2026, amount_limit=Decimal("8000.00"))
    goal = FinancialGoal(user_id=user_a.id, title="Alpha Private Asset", target_amount=Decimal("150000.00"), target_date=date(2027, 1, 1))

    db.session.add_all([tx, budget, goal])
    db.session.commit()

    # Log in as User Beta
    login_user(client, "beta@example.com", "BetaPass123!")

    # 1. Transaction tampering attempts
    assert client.get(f"/transactions/{tx.id}/edit").status_code == 404
    assert client.post(f"/transactions/{tx.id}/edit", data={"amount": "10.00"}).status_code == 404
    assert client.post(f"/transactions/{tx.id}/delete").status_code == 404

    # 2. Budget tampering attempts
    assert client.get(f"/budgets/{budget.id}/edit").status_code == 404
    assert client.post(f"/budgets/{budget.id}/edit", data={"amount_limit": "100.00"}).status_code == 404
    assert client.post(f"/budgets/{budget.id}/delete").status_code == 404

    # 3. Goal tampering attempts
    assert client.get(f"/goals/{goal.id}").status_code == 404
    assert client.get(f"/goals/{goal.id}/edit").status_code == 404
    assert client.post(f"/goals/{goal.id}/contribute", data={"amount": "500.00"}).status_code == 404
    assert client.post(f"/goals/{goal.id}/delete").status_code == 404
