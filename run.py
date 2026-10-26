from app import create_app
from app.extensions import db
from app.models import (
    User,
    Category,
    Transaction,
    Budget,
    FinancialGoal,
    SavingsContribution,
    Notification,
    ExpensePrediction,
)

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Make models and db session available in 'flask shell' for fast debugging."""
    return {
        "db": db,
        "User": User,
        "Category": Category,
        "Transaction": Transaction,
        "Budget": Budget,
        "FinancialGoal": FinancialGoal,
        "SavingsContribution": SavingsContribution,
        "Notification": Notification,
        "ExpensePrediction": ExpensePrediction,
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
