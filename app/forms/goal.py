from datetime import date, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError


class FinancialGoalForm(FlaskForm):
    """Form for setting up a milestone savings goal."""
    title = StringField(
        "Goal Title",
        validators=[
            DataRequired(message="Goal title is required."),
            Length(min=2, max=120, message="Title must be between 2 and 120 characters."),
        ],
        render_kw={"placeholder": "e.g. New MacBook Pro / Emergency Fund"},
    )
    target_amount = DecimalField(
        "Target Amount",
        places=2,
        validators=[
            DataRequired(message="Target amount is required."),
            NumberRange(min=1.00, max=99999999.99, message="Target amount must be at least 1.00."),
        ],
        render_kw={"placeholder": "e.g. 120000.00", "step": "0.01"},
    )
    current_amount = DecimalField(
        "Initial Saved Amount",
        places=2,
        default=0.00,
        validators=[
            Optional(),
            NumberRange(min=0.00, max=99999999.99, message="Current amount cannot be negative."),
        ],
        render_kw={"placeholder": "0.00", "step": "0.01"},
    )
    target_date = DateField(
        "Target Completion Date",
        default=lambda: date.today() + timedelta(days=180),
        validators=[DataRequired(message="Target date is required.")],
    )
    notes = TextAreaField(
        "Notes / Purpose (Optional)",
        validators=[Optional(), Length(max=500, message="Notes cannot exceed 500 characters.")],
        render_kw={"placeholder": "Why is this goal important? What is your savings plan?", "rows": 3},
    )
    submit = SubmitField("Save Financial Goal")

    def validate_target_date(self, field):
        """Ensure deadline is not in the past for new goals."""
        if field.data and field.data < date.today():
            raise ValidationError("Target deadline must be in the future.")


class SavingsContributionForm(FlaskForm):
    """Form for logging a contribution towards an active financial goal."""
    amount = DecimalField(
        "Contribution Amount",
        places=2,
        validators=[
            DataRequired(message="Contribution amount is required."),
            NumberRange(min=0.01, max=99999999.99, message="Contribution must be at least 0.01."),
        ],
        render_kw={"placeholder": "e.g. 5000.00", "step": "0.01"},
    )
    contribution_date = DateField(
        "Contribution Date",
        default=date.today,
        validators=[DataRequired(message="Date is required.")],
    )
    notes = StringField(
        "Note / Source (Optional)",
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "e.g. Monthly salary savings deposit"},
    )
    submit = SubmitField("Deposit Contribution")
