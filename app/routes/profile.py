from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.forms.profile import ProfileForm, ChangePasswordForm

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    """View and update profile information and preferred currency."""
    profile_form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if profile_form.validate_on_submit() and "profile_submit" in request.form:
        current_user.full_name = profile_form.full_name.data.strip()
        current_user.currency = profile_form.currency.data
        db.session.commit()
        flash("Profile information updated successfully!", "success")
        return redirect(url_for("profile.index"))

    return render_template(
        "profile/profile.html",
        profile_form=profile_form,
        password_form=password_form,
    )


@profile_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """Securely update the user's password."""
    password_form = ChangePasswordForm()

    if password_form.validate_on_submit():
        if current_user.check_password(password_form.current_password.data):
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash("Your password has been changed successfully!", "success")
            return redirect(url_for("profile.index"))
        else:
            flash("Current password was incorrect. Please try again.", "danger")
            return redirect(url_for("profile.index"))

    # If validation failed (e.g. password mismatch or too short)
    for field, errors in password_form.errors.items():
        for error in errors:
            flash(f"Password Error: {error}", "danger")

    return redirect(url_for("profile.index"))
