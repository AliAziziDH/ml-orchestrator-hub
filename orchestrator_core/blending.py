
import numpy as np
from scipy.optimize import minimize


def optimize_ensemble_weights(
    oof_predictions: np.ndarray,
    y_true: np.ndarray,
    objective: str = "rmsle",
    allow_negative: bool = False,
) -> np.ndarray:
    """
    Optimize ensemble weights using SLSQP constraints.

    Args:
        oof_predictions: 2D numpy array of shape (n_samples, n_models).
        y_true: 1D numpy array of shape (n_samples,).
        objective: 'rmsle' or 'rmse' or 'mse' (default 'rmsle').
        allow_negative: If False, enforces w_i >= 0.

    Returns:
        1D numpy array of optimized weights of shape (n_models,).
    """
    _, n_models = oof_predictions.shape

    # Initial weights: uniform distribution
    initial_weights = np.ones(n_models) / n_models

    # Constraints: sum of weights = 1
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    # Bounds: w_i >= 0 if allow_negative is False, else no bounds
    bounds = [(0.0, 1.0) if not allow_negative else (None, None)] * n_models

    def loss_func(weights: np.ndarray) -> float:
        # Compute weighted predictions
        preds = np.dot(oof_predictions, weights)

        if objective == "rmsle":
            # Optimization directly in log-space for RMSLE
            # Avoid log(<= 0) by clipping
            clipped_preds = np.clip(preds, a_min=0, a_max=None)
            log_preds = np.log1p(clipped_preds)
            log_true = np.log1p(np.clip(y_true, a_min=0, a_max=None))
            return float(np.sqrt(np.mean((log_preds - log_true) ** 2)))
        elif objective == "rmse":
            return float(np.sqrt(np.mean((preds - y_true) ** 2)))
        elif objective == "mse":
            return float(np.mean((preds - y_true) ** 2))
        else:
            raise ValueError(f"Unknown objective function: {objective}")

    result = minimize(
        loss_func,
        initial_weights,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )

    if not result.success:
        import warnings

        warnings.warn(f"Optimization failed: {result.message}")

    return result.x
