import numpy as np

from orchestrator_core.metrics import pass_at_k, root_mean_squared_log_error


def test_rmsle():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.0, 2.0, 3.0])

    rmsle = root_mean_squared_log_error(y_true, y_pred)
    assert np.isclose(rmsle, 0.0)

    y_pred2 = np.array([-1.0, -2.0, -3.0])
    rmsle2 = root_mean_squared_log_error(y_true, y_pred2)
    # y_pred2 gets clipped to 0
    # log_true = log1p([1, 2, 3]) = [0.693, 1.098, 1.386]
    # log_pred = log1p([0, 0, 0]) = [0, 0, 0]
    expected = np.sqrt(np.mean(np.log1p(y_true) ** 2))
    assert np.isclose(rmsle2, expected)


def test_pass_at_k():
    # n=1, c=1, k=1 -> pass@1 = 1.0
    assert np.isclose(pass_at_k(1, 1, 1), 1.0)

    # n=1, c=0, k=1 -> pass@1 = 0.0
    assert np.isclose(pass_at_k(1, 0, 1), 0.0)

    # n=10, c=5, k=2
    # expected: 1 - comb(10-5, 2)/comb(10, 2)
    # comb(5,2) = 10, comb(10,2) = 45 -> 1 - 10/45 = 35/45 = 7/9 ≈ 0.7777
    assert np.isclose(pass_at_k(10, 5, 2), 7.0 / 9.0)

    # Large numbers testing stability
    # Should not overflow/underflow
    res = pass_at_k(1000, 50, 10)
    assert 0 <= res <= 1.0
