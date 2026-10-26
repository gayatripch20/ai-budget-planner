from datetime import date
from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class BudgetForm(FlaskForm):
    """Form for setting or updating monthly category spending limits."""
    category_id = SelectField(
        "Expense Category",
        coerce=int,
        validators=[DataRequired(message="Please select an expense category.")],
    )
    month = SelectField(
        "Month",
        coerce=int,
        choices=[
            (1, "January"),
            (2, "February"),
            (3, "March"),
            (4, "April"),
            (5, "May"),
            (6, "June"),
            (7, "July"),
            (8, "August"),
            (9, "September"),
            (10, "October"),
            (11, "November"),
            (12, "December"),
        ],
        default=date.today().month,
        validators=[DataRequired()],
    )
    year = IntegerField(
        "Year",
        default=date.today().year,
        validators=[
            DataRequired(message="Year is required."),
            NumberRange(min=2020, max=2100, message="Please enter a valid year."),
        ],
    )
    amount_limit = DecimalField(
        "Monthly Spending Limit",
        places=2,
        validators=[
            DataRequired(message="Budget limit is required."),
            NumberRange(min=1.00, max=99999999.99, message="Budget limit must be at least 1.00."),
        ],
        render_kw={"placeholder": "e.g. 10000.00", "step": "0.01"},
    )
    submit = SubmitField("Save Budget")
