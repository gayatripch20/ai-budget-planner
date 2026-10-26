from datetime import date
import json
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from ml.forecasting import ExpenseForecaster
from app.services.recommendations import generate_smart_recommendations

predictions_bp = Blueprint("predictions", __name__, url_prefix="/predictions")


@predictions_bp.route("/")
@login_required
def index():
    """Display machine learning expense forecasts and smart recommendations."""
    today = date.today()

    # 1. Run Machine Learning Expense Forecaster
    forecast = ExpenseForecaster.forecast_next_month(current_user.id)

    # 2. Run Smart Financial Recommendation Engine
    rec_results = generate_smart_recommendations(
        user_id=current_user.id,
        year=today.year,
        month=today.month,
        forecast_amount=forecast["predicted_amount"],
    )

    # 3. Construct Chart.js payload: Past Actuals + Next Predicted Month
    chart_labels = list(forecast["historical_labels"])
    actual_data = list(forecast["historical_values"])
    predicted_data = [None] * len(actual_data)

    if chart_labels:
        # Append forecast point
        next_label = f"{forecast['forecast_month']:02d}/{forecast['forecast_year']} (Est)"
        chart_labels.append(next_label)
        actual_data.append(None)
        # Connect last actual point to predicted point for visual continuity
        predicted_data[-1] = forecast["historical_values"][-1]
        predicted_data.append(forecast["predicted_amount"])

    forecast_chart_payload = {
        "labels": chart_labels,
        "actual": actual_data,
        "predicted": predicted_data,
    }

    return render_template(
        "predictions/forecast_and_insights.html",
        forecast=forecast,
        rule_50_30_20=rec_results["rule_50_30_20"],
        recommendations=rec_results["recommendations"],
        forecast_chart_json=json.dumps(forecast_chart_payload, default=float),
    )
