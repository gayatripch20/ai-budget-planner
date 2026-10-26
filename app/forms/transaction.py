from datetime import date
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, DateField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional


class TransactionForm(FlaskForm):
    """
    Form for adding and editing financial transactions (Income or Expense).
    Validates monetary precision, date format, and category association.
    """
    amount = DecimalField(
        "Amount",
        places=2,
        validators=[
            DataRequired(message="Amount is required."),
            NumberRange(min=0.01, max=99999999.99, message="Amount must be between 0.01 and 99,999,999.99"),
        ],
        render_kw={"placeholder": "0.00", "step": "0.01"},
    )
    category_id = SelectField(
        "Category",
        coerce=int,
        validators=[DataRequired(message="Please select a category.")],
    )
    transaction_date = DateField(
        "Transaction Date",
        default=date.today,
        validators=[DataRequired(message="Date is required.")],
    )
    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("Cash", "Cash"),
            ("UPI", "UPI (Google Pay, PhonePe, Paytm)"),
            ("Debit Card", "Debit Card"),
            ("Credit Card", "Credit Card"),
            ("Net Banking", "Net Banking"),
            ("Other", "Other"),
        ],
        default="UPI",
        validators=[DataRequired(message="Payment method is required.")],
    )
    description = StringField(
        "Description / Note (Optional)",
        validators=[
            Optional(),
            Length(max=255, message="Description cannot exceed 255 characters."),
        ],
        render_kw={"placeholder": "e.g., Monthly grocery shopping at DMart"},
    )
    submit = SubmitField("Save Transaction")


class TransactionFilterForm(FlaskForm):
    """Form for filtering and searching transactions in history tables."""
    category_id = SelectField("Category", coerce=int, validators=[Optional()])
    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("", "All Payment Methods"),
            ("Cash", "Cash"),
            ("UPI", "UPI"),
            ("Debit Card", "Debit Card"),
            ("Credit Card", "Credit Card"),
            ("Net Banking", "Net Banking"),
            ("Other", "Other"),
        ],
        default="",
        validators=[Optional()],
    )
    start_date = DateField("From Date", validators=[Optional()])
    end_date = DateField("To Date", validators=[Optional()])
    search = StringField(
        "Search Description",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Keyword..."},
    )
    submit = SubmitField("Apply Filters")
