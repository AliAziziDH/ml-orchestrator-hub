import numpy as np

from orchestrator_core.blending import optimize_ensemble_weights


def test_optimize_ensemble_weights_rmse():
    # True values
    y_true = np.array([1.0, 2.0, 3.0, 4.0])

    # Model 1 is perfect, Model 2 is bad
    m1 = np.array([1.0, 2.0, 3.0, 4.0])
    m2 = np.array([0.0, 0.0, 0.0, 0.0])

    oof_predictions = np.column_stack([m1, m2])

    weights = optimize_ensemble_weights(
        oof_predictions, y_true, objective="rmse", allow_negative=False
    )

    # Model 1 should get weight ~1, Model 2 ~0
    assert np.allclose(weights, [1.0, 0.0], atol=1e-3)
    assert np.allclose(np.sum(weights), 1.0)


def test_optimize_ensemble_weights_rmsle():
    y_true = np.array([10.0, 100.0, 1000.0])

    m1 = np.array([10.0, 100.0, 1000.0])
    m2 = np.array([1.0, 10.0, 100.0])

    oof_predictions = np.column_stack([m1, m2])

    weights = optimize_ensemble_weights(
        oof_predictions, y_true, objective="rmsle", allow_negative=False
    )

    assert np.allclose(weights, [1.0, 0.0], atol=1e-3)
    assert np.allclose(np.sum(weights), 1.0)
