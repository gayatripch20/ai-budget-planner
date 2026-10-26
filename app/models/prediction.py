from datetime import datetime, timezone
from app.extensions import db


class ExpensePrediction(db.Model):
    """
    Historical record of machine learning forecasts and baseline projections.
    Keeps audit trail of prediction models, accuracy metrics (MAE), and projected spending.
    """
    __tablename__ = "expense_predictions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_month = db.Column(db.Integer, nullable=False)
    forecast_year = db.Column(db.Integer, nullable=False)
    predicted_amount = db.Column(db.Numeric(12, 2), nullable=False)
    model_used = db.Column(db.String(50), nullable=False)  # 'LinearRegression', 'MovingAverageBaseline'
    mae_score = db.Column(db.Numeric(8, 2), nullable=True)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<ExpensePrediction id={self.id} user={self.user_id} {self.forecast_month}/{self.forecast_year} amount={self.predicted_amount}>"
