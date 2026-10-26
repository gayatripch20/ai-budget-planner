"""
Automated Test Suite for Income and Expense Transaction Management.
Validates transaction CRUD operations, data isolation across multiple users,
search/filtering logic, and decimal amount validation.
"""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction


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


def test_add_income_transaction(client):
    """Verify adding an income transaction."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    salary_cat = Category.query.filter_by(name="Salary").first()

    response = client.post(
        "/transactions/new/income",
        data={
            "amount": "45000.00",
            "category_id": salary_cat.id,
            "transaction_date": date.today().isoformat(),
            "payment_method": "Net Banking",
            "description": "October Monthly Salary",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Income of \xe2\x82\xb945000.00 recorded successfully!" in response.data or b"recorded successfully!" in response.data

    user = User.query.filter_by(email="alpha@example.com").first()
    tx = Transaction.query.filter_by(user_id=user.id, transaction_type="income").first()
    assert tx is not None
    assert tx.amount == Decimal("45000.00")
    assert tx.payment_method == "Net Banking"


def test_add_expense_transaction(client):
    """Verify adding an expense transaction."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    response = client.post(
        "/transactions/new/expense",
        data={
            "amount": "850.50",
            "category_id": food_cat.id,
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
            "description": "Dinner with friends",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"recorded successfully!" in response.data

    user = User.query.filter_by(email="alpha@example.com").first()
    tx = Transaction.query.filter_by(user_id=user.id, transaction_type="expense").first()
    assert tx is not None
    assert tx.amount == Decimal("850.50")


def test_negative_or_zero_amount_rejected(client):
    """Verify that zero or negative transaction amounts are rejected."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    response = client.post(
        "/transactions/new/expense",
        data={
            "amount": "-50.00",
            "category_id": food_cat.id,
            "transaction_date": date.today().isoformat(),
            "payment_method": "Cash",
            "description": "Invalid negative entry",
        },
    )
    assert response.status_code == 200
    assert b"Amount must be between 0.01 and 99,999,999.99" in response.data


def test_edit_own_transaction(client):
    """Verify updating an existing transaction."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    tx = Transaction(
        user_id=user.id,
        category_id=food_cat.id,
        transaction_type="expense",
        amount=Decimal("500.00"),
        transaction_date=date.today(),
        payment_method="Cash",
        description="Lunch",
    )
    db.session.add(tx)
    db.session.commit()

    # Edit transaction
    response = client.post(
        f"/transactions/{tx.id}/edit",
        data={
            "amount": "650.00",
            "category_id": food_cat.id,
            "transaction_date": date.today().isoformat(),
            "payment_method": "UPI",
            "description": "Lunch and dessert",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Transaction updated successfully!" in response.data

    updated_tx = db.session.get(Transaction, tx.id)
    assert updated_tx.amount == Decimal("650.00")
    assert updated_tx.payment_method == "UPI"
    assert updated_tx.description == "Lunch and dessert"


def test_delete_own_transaction(client):
    """Verify deleting a transaction."""
    login_user(client, "alpha@example.com", "AlphaPass123!")
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    tx = Transaction(
        user_id=user.id,
        category_id=food_cat.id,
        transaction_type="expense",
        amount=Decimal("300.00"),
        transaction_date=date.today(),
        payment_method="Cash",
    )
    db.session.add(tx)
    db.session.commit()
    tx_id = tx.id

    response = client.post(f"/transactions/{tx_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Transaction deleted successfully." in response.data

    assert db.session.get(Transaction, tx_id) is None


def test_cross_user_data_isolation(client):
    """
    CRITICAL SECURITY TEST:
    Verify that User Beta cannot view, edit, or delete User Alpha's transactions.
    """
    user_a = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    # User Alpha creates a private transaction
    tx_a = Transaction(
        user_id=user_a.id,
        category_id=food_cat.id,
        transaction_type="expense",
        amount=Decimal("1200.00"),
        transaction_date=date.today(),
        payment_method="Credit Card",
        description="Alpha Private Spend",
    )
    db.session.add(tx_a)
    db.session.commit()

    # Now log in as User Beta
    login_user(client, "beta@example.com", "BetaPass123!")

    # 1. User Beta cannot view User Alpha's transaction in their list
    list_res = client.get("/transactions/expense")
    assert b"Alpha Private Spend" not in list_res.data

    # 2. User Beta cannot edit User Alpha's transaction (HTTP 404)
    edit_res = client.get(f"/transactions/{tx_a.id}/edit")
    assert edit_res.status_code == 404

    # 3. User Beta cannot delete User Alpha's transaction (HTTP 404)
    del_res = client.post(f"/transactions/{tx_a.id}/delete")
    assert del_res.status_code == 404

    # Confirm record was not deleted
    assert db.session.get(Transaction, tx_a.id) is not None
