import numpy as np

from orchestrator_core.conformal import compute_conformal_quantile, predict_conformal_bounds


def test_conformal_prediction():
    # 9 points, n=9.
    # alpha = 0.1
    # q_level = ceil((10)*0.9) / 9 = ceil(9)/9 = 1.0
    # quantile should be the max

    residuals = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    q_val = compute_conformal_quantile(residuals, alpha=0.1)

    assert np.isclose(q_val, 0.9)

    preds = np.array([10.0, 20.0])
    lower, upper = predict_conformal_bounds(preds, q_val)

    assert np.allclose(lower, [9.1, 19.1])
    assert np.allclose(upper, [10.9, 20.9])
