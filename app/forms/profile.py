from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class ProfileForm(FlaskForm):
    """Form for updating user profile settings and preferred currency."""
    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
        ],
    )
    currency = SelectField(
        "Preferred Currency",
        choices=[
            ("₹", "₹ INR - Indian Rupee"),
            ("$", "$ USD - US Dollar"),
            ("€", "€ EUR - Euro"),
            ("£", "£ GBP - British Pound"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Save Profile Changes")


class ChangePasswordForm(FlaskForm):
    """Form for updating user account password."""
    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(message="Current password is required.")],
    )
    new_password = PasswordField(
        "New Password",
        validators=[
            DataRequired(message="New password is required."),
            Length(min=6, max=64, message="Password must be at least 6 characters."),
        ],
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(message="Please confirm your new password."),
            EqualTo("new_password", message="New passwords must match exactly."),
        ],
    )
    submit = SubmitField("Update Password")
