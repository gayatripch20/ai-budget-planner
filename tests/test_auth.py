"""
Automated Test Suite for User Authentication and Authorization.
Validates registration validation rules, login flows, password checks, session state, and route protection.
"""
import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.notification import Notification


@pytest.fixture
def app():
    """Create test application context configured for testing."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for issuing HTTP requests and tracking sessions."""
    return app.test_client()


def test_landing_page_accessible(client):
    """Verify that the public landing page loads properly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Master Your Finances" in response.data


def test_registration_success(client):
    """Verify that a new user can register successfully."""
    response = client.post(
        "/auth/register",
        data={
            "full_name": "Arjun Kumar",
            "email": "arjun@example.com",
            "currency": "₹",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Your account has been registered successfully" in response.data

    # Verify user exists in database
    user = User.query.filter_by(email="arjun@example.com").first()
    assert user is not None
    assert user.full_name == "Arjun Kumar"
    assert user.currency == "₹"
    assert user.check_password("Password123!") is True

    # Verify welcome notification
    notif = Notification.query.filter_by(user_id=user.id).first()
    assert notif is not None
    assert "Welcome" in notif.title


def test_registration_duplicate_email_rejected(client):
    """Verify that duplicate email registration is rejected with validation error."""
    # Register first user
    user = User(full_name="First User", email="duplicate@example.com")
    user.set_password("Secret123")
    db.session.add(user)
    db.session.commit()

    # Attempt to register again with same email
    response = client.post(
        "/auth/register",
        data={
            "full_name": "Second User",
            "email": "duplicate@example.com",
            "currency": "₹",
            "password": "NewSecret123",
            "confirm_password": "NewSecret123",
        },
    )
    assert response.status_code == 200
    assert b"already exists" in response.data


def test_registration_password_mismatch_rejected(client):
    """Verify that mismatched passwords fail validation."""
    response = client.post(
        "/auth/register",
        data={
            "full_name": "Test User",
            "email": "mismatch@example.com",
            "currency": "₹",
            "password": "Password123",
            "confirm_password": "DifferentPassword456",
        },
    )
    assert response.status_code == 200
    assert b"Passwords must match exactly" in response.data


def test_login_success_and_logout(client):
    """Verify successful login, session establishment, and logout."""
    user = User(full_name="Kavita Nair", email="kavita@example.com")
    user.set_password("MySecretPass88")
    db.session.add(user)
    db.session.commit()

    # Perform login
    login_res = client.post(
        "/auth/login",
        data={"email": "kavita@example.com", "password": "MySecretPass88"},
        follow_redirects=True,
    )
    assert login_res.status_code == 200
    assert b"Welcome back, Kavita Nair" in login_res.data
    assert b"Financial Dashboard" in login_res.data

    # Perform logout
    logout_res = client.get("/auth/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"You have been safely logged out" in logout_res.data


def test_login_invalid_credentials(client):
    """Verify that incorrect passwords are rejected."""
    user = User(full_name="Sanjay Patel", email="sanjay@example.com")
    user.set_password("CorrectPass")
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "sanjay@example.com", "password": "WrongPassword"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid email address or password" in response.data


def test_protected_route_requires_login(client):
    """Verify that unauthenticated users attempting to access /dashboard are redirected to login."""
    response = client.get("/dashboard/", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
