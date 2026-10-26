"""
Machine Learning Forecasting Module.
Implements a multi-tiered expense prediction strategy:
- Tier 1 (< 3 months): Moving Average baseline with honest data scarcity disclosures.
- Tier 2 (3 to 5 months): Scikit-learn Linear Trend Regression.
- Tier 3 (6+ months): Scikit-learn Regularized Ridge Regression with lag and cyclical features.
Evaluated via Mean Absolute Error (MAE) and persisted for auditability.
"""
from datetime import date
from decimal import Decimal
from typing import Dict, Any, Optional
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from app.extensions import db
from app.models.prediction import ExpensePrediction
from ml.preprocessing import prepare_monthly_expense_series
from ml.evaluation import compute_mae, compare_against_baseline


class ExpenseForecaster:
    """Core predictive engine for personal financial expense forecasting."""

    @staticmethod
    def forecast_next_month(user_id: int) -> Dict[str, Any]:
        """
        Generate next month's predicted expense based on historical data volume.
        """
        df = prepare_monthly_expense_series(user_id)
        today = date.today()

        # Determine upcoming forecast month and year
        if df.empty:
            next_month = 1 if today.month == 12 else today.month + 1
            next_year = today.year + 1 if today.month == 12 else today.year
            return {
                "forecast_month": next_month,
                "forecast_year": next_year,
                "predicted_amount": 0.00,
                "model_used": "NoData",
                "mae_score": None,
                "confidence": "none",
                "explanation": "No expense transactions logged yet. Log transactions across multiple months to activate AI forecasting.",
                "historical_labels": [],
                "historical_values": [],
                "baseline_comparison": None,
            }

        last_row = df.iloc[-1]
        last_yr, last_mo = int(last_row["year"]), int(last_row["month"])
        next_month = 1 if last_mo == 12 else last_mo + 1
        next_year = last_yr + 1 if last_mo == 12 else last_yr

        n_records = len(df)
        historical_labels = [f"{int(r.month):02d}/{int(r.year)}" for _, r in df.iterrows()]
        historical_values = [round(float(r.total_expense), 2) for _, r in df.iterrows()]

        # -------------------------------------------------------------------------
        # TIER 1: COLD START (< 3 months)
        # -------------------------------------------------------------------------
        if n_records < 3:
            pred_val = float(df["total_expense"].mean())
            model_name = "MovingAverageBaseline"
            confidence = "low"
            mae_score = None
            explanation = (
                f"Preliminary estimate based on historical mean ({n_records} month(s) of records). "
                "At least 3 months of transaction history are required to train a personalized machine learning model."
            )
            comparison = None

        # -------------------------------------------------------------------------
        # TIER 2: MODERATE HISTORY (3 to 5 months)
        # -------------------------------------------------------------------------
        elif 3 <= n_records < 6:
            X = df[["period_index"]].values
            y = df["total_expense"].values

            model = LinearRegression()
            model.fit(X, y)

            # Predict next period
            next_period = np.array([[n_records + 1]])
            pred_val = max(0.0, float(model.predict(next_period)[0]))

            # In-sample evaluation vs baseline
            y_pred_hist = model.predict(X)
            y_base_hist = np.full_like(y, fill_value=np.mean(y))
            comparison = compare_against_baseline(y, y_pred_hist, y_base_hist)
            mae_score = comparison["model_mae"]

            model_name = "LinearTrendRegression"
            confidence = "moderate"
            explanation = (
                f"Trained using Scikit-Learn Linear Trend Regression across {n_records} historical months. "
                f"Average historical error (MAE): ±₹{mae_score:.2f}."
            )

        # -------------------------------------------------------------------------
        # TIER 3: RICH TIME-SERIES HISTORY (6+ months)
        # -------------------------------------------------------------------------
        else:
            # Feature engineering: time index, lag-1, cyclical month sine/cosine
            df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
            df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

            feature_cols = ["period_index", "lag_1", "month_sin", "month_cos"]
            X = df[feature_cols].values
            y = df["total_expense"].values

            # Temporal train/test split: train on past, evaluate on most recent point
            X_train, y_train = X[:-1], y[:-1]
            X_test, y_test = X[-1:], y[-1:]

            model = Ridge(alpha=1.0)
            model.fit(X_train, y_train)

            # Evaluation on test holdout
            test_pred = model.predict(X_test)
            mae_score = round(float(compute_mae(y_test, test_pred)), 2)

            # Re-fit on all data to forecast future
            model.fit(X, y)
            next_features = np.array([[
                n_records + 1,
                df["total_expense"].iloc[-1],
                np.sin(2 * np.pi * next_month / 12),
                np.cos(2 * np.pi * next_month / 12),
            ]])
            pred_val = max(0.0, float(model.predict(next_features)[0]))

            y_base = np.full_like(y, fill_value=np.mean(y))
            comparison = compare_against_baseline(y, model.predict(X), y_base)

            model_name = "RidgeTimeSeriesRegression"
            confidence = "high"
            explanation = (
                f"Trained using Scikit-Learn Regularized Ridge Regression with lag and cyclical features across {n_records} months. "
                f"Test evaluation holdout MAE: ±₹{mae_score:.2f}."
            )

        pred_val_rounded = round(pred_val, 2)

        # Persist forecast to database for auditing
        record = ExpensePrediction(
            user_id=user_id,
            forecast_month=next_month,
            forecast_year=next_year,
            predicted_amount=Decimal(str(pred_val_rounded)),
            model_used=model_name,
            mae_score=Decimal(str(mae_score)) if mae_score is not None else None,
        )
        db.session.add(record)
        db.session.commit()

        return {
            "forecast_month": next_month,
            "forecast_year": next_year,
            "predicted_amount": pred_val_rounded,
            "model_used": model_name,
            "mae_score": mae_score,
            "confidence": confidence,
            "explanation": explanation,
            "historical_labels": historical_labels,
            "historical_values": historical_values,
            "baseline_comparison": comparison,
        }
