from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user import User


class RegistrationForm(FlaskForm):
    """Form for registering a new user account with client & server-side validation."""
    full_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Full name is required."),
            Length(min=2, max=100, message="Full name must be between 2 and 100 characters."),
        ],
        render_kw={"placeholder": "e.g. Rahul Sharma"},
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email address is required."),
            Email(message="Please enter a valid email address."),
            Length(max=120, message="Email cannot exceed 120 characters."),
        ],
        render_kw={"placeholder": "name@example.com"},
    )
    currency = SelectField(
        "Preferred Currency",
        choices=[
            ("₹", "₹ INR - Indian Rupee"),
            ("$", "$ USD - US Dollar"),
            ("€", "€ EUR - Euro"),
            ("£", "£ GBP - British Pound"),
        ],
        default="₹",
        validators=[DataRequired()],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=6, max=64, message="Password must be at least 6 characters."),
        ],
        render_kw={"placeholder": "At least 6 characters"},
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match exactly."),
        ],
        render_kw={"placeholder": "Re-enter your password"},
    )
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        """Verify that the email is not already registered."""
        email_clean = field.data.strip().lower()
        if User.query.filter_by(email=email_clean).first():
            raise ValidationError("An account with this email address already exists. Please log in.")


class LoginForm(FlaskForm):
    """Form for authenticating an existing user."""
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Email is required."),
            Email(message="Please enter a valid email address."),
        ],
        render_kw={"placeholder": "name@example.com"},
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")],
        render_kw={"placeholder": "Enter your password"},
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Log In")
