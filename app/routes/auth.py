from urllib.parse import urlsplit
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models.user import User
from app.models.notification import Notification
from app.forms.auth import RegistrationForm, LoginForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Handle new user registration."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data.strip().lower(),
            currency=form.currency.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Create an initial welcome notification
        welcome_note = Notification(
            user_id=user.id,
            title="Welcome to AI Budget Planner",
            message="Your account was created successfully! Get started by logging your income and setting your category budgets.",
            notification_type="info",
        )
        db.session.add(welcome_note)
        db.session.commit()

        flash("Your account has been registered successfully! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate an existing user and initiate a secure session."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome back, {user.full_name}!", "success")

            # Prevent Open Redirect vulnerability by ensuring 'next' points to a local URL path
            next_page = request.args.get("next")
            if not next_page or urlsplit(next_page).netloc != "":
                next_page = url_for("main.index")

            return redirect(next_page)
        else:
            flash("Invalid email address or password. Please try again.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Terminate the authenticated user's session."""
    logout_user()
    flash("You have been safely logged out.", "info")
    return redirect(url_for("auth.login"))
