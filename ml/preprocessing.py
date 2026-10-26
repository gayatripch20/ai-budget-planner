"""
Machine Learning Preprocessing Module.
Aggregates historical transactions into time-series monthly expenditure sequences
and constructs lag features for regression forecasting.
"""
from datetime import date
from decimal import Decimal
from typing import Tuple, List, Dict, Any
import pandas as pd
import numpy as np
from sqlalchemy import func, extract
from app.extensions import db
from app.models.transaction import Transaction


def prepare_monthly_expense_series(user_id: int) -> pd.DataFrame:
    """
    Extract and structure all historical expense transactions for a user
    into a continuous chronological monthly time series.
    
    Returns:
        pd.DataFrame with columns: ['year', 'month', 'year_month', 'period_index', 'total_expense']
    """
    # Query monthly summed expenses from MySQL
    results = (
        db.session.query(
            extract("year", Transaction.transaction_date).label("year"),
            extract("month", Transaction.transaction_date).label("month"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total_expense"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    if not results:
        return pd.DataFrame(columns=["year", "month", "year_month", "period_index", "total_expense", "lag_1"])

    data = []
    for r in results:
        yr = int(r.year)
        mo = int(r.month)
        amt = float(r.total_expense)
        data.append({
            "year": yr,
            "month": mo,
            "year_month": f"{yr}-{mo:02d}",
            "total_expense": amt,
        })

    df = pd.DataFrame(data)
    df["period_index"] = np.arange(1, len(df) + 1)
    df["lag_1"] = df["total_expense"].shift(1).fillna(df["total_expense"].iloc[0])

    return df
