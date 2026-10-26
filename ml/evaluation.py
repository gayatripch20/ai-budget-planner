"""
Machine Learning Evaluation Module.
Implements evaluation metrics (Mean Absolute Error, Baseline Comparisons).
"""
import numpy as np


def compute_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Mean Absolute Error (MAE):
    MAE = (1 / n) * sum(|y_true - y_pred|)
    MAE is in the exact unit of the currency (e.g. ₹ Rupees).
    """
    if len(y_true) == 0:
        return 0.0
    return float(np.mean(np.abs(y_true - y_pred)))


def compare_against_baseline(y_true: np.ndarray, y_pred: np.ndarray, y_baseline: np.ndarray) -> dict:
    """
    Compare regression model MAE against a naive historical mean baseline.
    Returns:
        dict with model_mae, baseline_mae, and percent_improvement
    """
    model_mae = compute_mae(y_true, y_pred)
    base_mae = compute_mae(y_true, y_baseline)

    pct_imp = 0.0
    if base_mae > 0:
        pct_imp = round(((base_mae - model_mae) / base_mae) * 100.0, 1)

    return {
        "model_mae": round(model_mae, 2),
        "baseline_mae": round(base_mae, 2),
        "percentage_improvement": pct_imp,
    }
