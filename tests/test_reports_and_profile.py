"""
Automated Test Suite for Reports, CSV/PDF Data Exports, and Profile Settings.
Validates CSV formatting, ReportLab PDF generation, profile updates, secure password change,
and multi-tenant export isolation.
"""
from datetime import date
from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.reports import generate_csv_report, generate_pdf_report


@pytest.fixture
def app():
    """Create test application context configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()

        # Seed category
        salary_cat = Category(name="Salary", type="income", icon="bi-cash", color="#1cc88a", is_default=True)
        food_cat = Category(name="Food & Dining", type="expense", icon="bi-cup", color="#e74a3b", is_default=True)
        db.session.add_all([salary_cat, food_cat])

        # Seed User A
        user_a = User(full_name="User Alpha", email="alpha@example.com", currency="₹")
        user_a.set_password("AlphaPass123!")
        db.session.add(user_a)

        # Seed User B
        user_b = User(full_name="User Beta", email="beta@example.com", currency="$")
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


def test_csv_report_generation(app):
    """Verify CSV export contains RFC 4180 headers and formatted transaction rows."""
    user = User.query.filter_by(email="alpha@example.com").first()
    salary_cat = Category.query.filter_by(name="Salary").first()

    tx = Transaction(
        user_id=user.id,
        category_id=salary_cat.id,
        transaction_type="income",
        amount=Decimal("55000.00"),
        transaction_date=date.today(),
        payment_method="Net Banking",
        description="October Salary Deposit",
    )
    db.session.add(tx)
    db.session.commit()

    csv_data = generate_csv_report(user)
    assert "Transaction ID,Date,Type,Category,Payment Method,Amount (\xe2\x82\xb9),Description" in csv_data or "Transaction ID" in csv_data
    assert "Income" in csv_data
    assert "Salary" in csv_data
    assert "55000.00" in csv_data
    assert "October Salary Deposit" in csv_data


def test_pdf_report_generation(app):
    """Verify ReportLab PDF generation outputs valid PDF binary bytes."""
    user = User.query.filter_by(email="alpha@example.com").first()
    food_cat = Category.query.filter_by(name="Food & Dining").first()

    tx = Transaction(
        user_id=user.id,
        category_id=food_cat.id,
        transaction_type="expense",
        amount=Decimal("1250.00"),
        transaction_date=date.today(),
        payment_method="UPI",
        description="Weekend groceries",
    )
    db.session.add(tx)
    db.session.commit()

    pdf_bytes = generate_pdf_report(user)
    assert isinstance(pdf_bytes, bytes)
    # Every valid PDF file starts with the %PDF magic header
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_export_endpoints(client):
    """Verify HTTP download endpoints for CSV and PDF export."""
    login_user(client, "alpha@example.com", "AlphaPass123!")

    # Test CSV download route
    csv_res = client.get("/reports/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.content_type
    assert "attachment; filename=" in csv_res.headers.get("Content-Disposition", "")

    # Test PDF download route
    pdf_res = client.get("/reports/export/pdf")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.content_type
    assert "attachment; filename=" in pdf_res.headers.get("Content-Disposition", "")


def test_profile_update(client):
    """Verify updating user full name and preferred currency symbol."""
    login_user(client, "alpha@example.com", "AlphaPass123!")

    response = client.post(
        "/profile/",
        data={
            "full_name": "Alpha Sharma",
            "currency": "$",
            "profile_submit": "1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Profile information updated successfully!" in response.data

    user = User.query.filter_by(email="alpha@example.com").first()
    assert user.full_name == "Alpha Sharma"
    assert user.currency == "$"


def test_password_change_success_and_failure(client):
    """Verify changing password with valid credentials, and rejecting invalid current password."""
    login_user(client, "alpha@example.com", "AlphaPass123!")

    # 1. Attempt with incorrect current password
    fail_res = client.post(
        "/profile/change-password",
        data={
            "current_password": "WrongPassword999",
            "new_password": "NewSecretPass456!",
            "confirm_new_password": "NewSecretPass456!",
        },
        follow_redirects=True,
    )
    assert fail_res.status_code == 200
    assert b"Current password was incorrect" in fail_res.data

    # 2. Attempt with correct current password
    success_res = client.post(
        "/profile/change-password",
        data={
            "current_password": "AlphaPass123!",
            "new_password": "NewSecretPass456!",
            "confirm_new_password": "NewSecretPass456!",
        },
        follow_redirects=True,
    )
    assert success_res.status_code == 200
    assert b"Your password has been changed successfully!" in success_res.data

    # Verify user can log in with new password
    user = User.query.filter_by(email="alpha@example.com").first()
    assert user.check_password("NewSecretPass456!") is True


def test_cross_user_report_isolation(client):
    """
    CRITICAL SECURITY TEST:
    Verify that User Beta cannot export or view User Alpha's financial statements.
    """
    user_a = User.query.filter_by(email="alpha@example.com").first()
    salary_cat = Category.query.filter_by(name="Salary").first()

    # User Alpha private transaction
    tx_a = Transaction(
        user_id=user_a.id,
        category_id=salary_cat.id,
        transaction_type="income",
        amount=Decimal("95000.00"),
        transaction_date=date.today(),
        payment_method="Net Banking",
        description="Alpha Super Secret Bonus",
    )
    db.session.add(tx_a)
    db.session.commit()

    # User Beta logs in and downloads CSV
    login_user(client, "beta@example.com", "BetaPass123!")
    csv_res = client.get("/reports/export/csv")
    assert csv_res.status_code == 200
    assert b"Alpha Super Secret Bonus" not in csv_res.data
    assert b"95000.00" not in csv_res.data
