# orchestrator_core

A modular, production-ready Python package designed as the central control plane and shared toolkit for multi-competition ML workflows.

## Installation

Install via pip directly from the source:

```bash
pip install -e .
```

To install development dependencies (like `pytest` and `ruff`):

```bash
pip install -e .[dev]
```

## Quickstart Usage

### Logging Experiments
Store atomic and persistent run records for your experiments.

```python
from orchestrator_core.ledger import log_experiment

log_experiment(
    project_name="HousingPrices",
    experiment_tag="baseline_lgbm",
    model_architecture="LightGBM",
    metric_name="RMSLE",
    oof_score=0.12,
    num_folds=5,
    key_insights="Baseline LightGBM model with default hyperparameters.",
)
```

### Optimize Ensemble Weights
Determine the optimal combination of Out-Of-Fold (OOF) predictions for your ensemble.

```python
import numpy as np
from orchestrator_core.blending import optimize_ensemble_weights

# Random predictions for 2 models
oof_preds = np.random.rand(100, 2)
y_true = np.random.rand(100)

weights = optimize_ensemble_weights(oof_preds, y_true, objective="rmse")
print(f"Optimal weights: {weights}")
```

### Conformal Prediction Intervals
Generate calibrated prediction bounds for regression.

```python
import numpy as np
from orchestrator_core.conformal import compute_conformal_quantile, predict_conformal_bounds

residuals = np.abs(y_true - oof_preds.mean(axis=1))

# Compute quantile on a calibration set
q_val = compute_conformal_quantile(residuals, alpha=0.10)

# Generate lower and upper bounds for test predictions
test_preds = np.random.rand(50)
lower, upper = predict_conformal_bounds(test_preds, q_val)
```

### Numerically Stable Metrics
Fast and stable metrics calculation.

```python
from orchestrator_core.metrics import root_mean_squared_log_error, pass_at_k

rmsle = root_mean_squared_log_error(y_true, oof_preds.mean(axis=1))

# Compute pass@k robustly
p_at_k = pass_at_k(n=10, c=2, k=5)
```

## Developer Guidelines
See `AGENTS.md` and `protocols/agent_rules.md` for our strict protocols on code quality and CV leakage prevention.
