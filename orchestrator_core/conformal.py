import numpy as np


def compute_conformal_quantile(residuals: np.ndarray, alpha: float = 0.10) -> float:
    """
    Compute the conformal quantile for residuals given a significance level alpha.

    Args:
        residuals: 1D numpy array of absolute residuals |y_true - y_pred|.
        alpha: Target miscoverage level (e.g., 0.10 for 90% coverage).

    Returns:
        The computed quantile q_val.
    """
    n = len(residuals)
    # The required quantile index formulation
    # P(|Y - \hat{Y}| <= q) >= 1 - alpha requires adjusting by (n+1)/n
    q_level = np.ceil((n + 1) * (1 - alpha)) / n
    q_level = np.clip(q_level, 0.0, 1.0)
    q_val = np.quantile(residuals, q_level, method="higher")
    return float(q_val)


def predict_conformal_bounds(preds: np.ndarray, q_val: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Predict the conformal prediction intervals.

    Args:
        preds: 1D numpy array of point predictions.
        q_val: The conformal quantile computed on a calibration set.

    Returns:
        Tuple of (lower_bounds, upper_bounds) as 1D numpy arrays.
    """
    lower_bounds = preds - q_val
    upper_bounds = preds + q_val
    return lower_bounds, upper_bounds
