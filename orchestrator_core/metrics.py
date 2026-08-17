import numpy as np
from scipy.special import gammaln


def root_mean_squared_log_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Compute Root Mean Squared Logarithmic Error.
    Clips predictions to prevent log(<= 0).
    """
    y_true_clipped = np.clip(y_true, a_min=0, a_max=None)
    y_pred_clipped = np.clip(y_pred, a_min=0, a_max=None)

    log_true = np.log1p(y_true_clipped)
    log_pred = np.log1p(y_pred_clipped)

    return float(np.sqrt(np.mean((log_pred - log_true) ** 2)))


def pass_at_k(n: int, c: int, k: int) -> float:
    """
    Compute pass@k metric robustly to avoid overflow/underflow.
    Used for program synthesis benchmarks.

    Args:
        n: Total number of generated samples.
        c: Number of correct samples.
        k: The k parameter in pass@k (e.g., pass@1, pass@10).

    Returns:
        The probability of at least one correct sample in k generations.
    """
    if n - c < k:
        return 1.0

    # Using log combinations for numerical stability
    # C(n-c, k) / C(n, k)
    # log C(a, b) = gammaln(a + 1) - gammaln(b + 1) - gammaln(a - b + 1)

    log_num = gammaln(n - c + 1) - gammaln(k + 1) - gammaln(n - c - k + 1)
    log_den = gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)

    prob_no_correct = np.exp(log_num - log_den)
    return float(1.0 - prob_no_correct)
