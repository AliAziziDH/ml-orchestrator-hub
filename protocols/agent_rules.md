# Downstream Agent Rules

These rules provide operational guidelines and standard protocols for AI agents working in downstream consumer repositories utilizing `orchestrator_core`.

## 1. Cross-Validation Leakage Prevention
- **Golden Rule**: Under no circumstances should test sets or public leaderboard data leak into the training process.
- Ensure that feature engineering happens strictly within each CV fold. For instance, do not compute global statistics on target features across the entire training dataset. Target encode inside folds.
- Cross-validation splits should always respect constraints (e.g. `GroupKFold` or `StratifiedGroupKFold`) when group overlaps exist.

## 2. Model Evaluation and Logging
- Every trained model **must** be logged through `orchestrator_core.ledger.log_experiment`.
- Ensure accurate documentation of `key_insights`. Describe hyperparameter changes, feature additions, or blending decisions.
- When generating out-of-fold (OOF) predictions, verify their shape exactly matches the corresponding target array's shape before computing metrics or storing the predictions.

## 3. Preprocessing and Ordinal Encoding
- When conducting ordinal encoding, specify unknown categories accurately. Use `-1` or another explicit marker when validation/test sets contain unseen categories.
- Missing values should be imputed separately within each fold if using statistical imputation (e.g., mean/median), or explicitly flagged (e.g. keeping NaN if supported natively by models like XGBoost, LightGBM, CatBoost).

## 4. Blending Protocols
- Downstream blend optimizations must rely on the provided `orchestrator_core.blending.optimize_ensemble_weights`.
- Never fit weights using the public leaderboard. Optimize blending weights using only Out-Of-Fold (OOF) predictions to prevent overfitting.
