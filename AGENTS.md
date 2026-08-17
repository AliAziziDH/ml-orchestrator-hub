# AGENTS.md

## Architectural Guidelines and Operational Rules for this Repository

Welcome to the `ml-orchestrator-hub` repository. If you are an AI agent operating inside this repo, you must adhere to the following rules:

### 1. Hub-and-Spoke Architecture
This repository (`ml-orchestrator-hub`) serves as the central **Control Plane (Hub)** for all automated multi-agent ML workflows. Downstream repositories (the "spokes" like `house-prices-kaggle`, `titanic`, etc.) depend on the tools provided here.

- **`orchestrator_core`**: The shared, installable Python library providing central logging, blending solvers, and evaluation metrics.
- **Single Source of Truth**: The centralized Ledger (Google Sheets/Cloud SQL) stores all experiment metadata globally.

#### Guidelines for Downstream Agents
If you are an agent operating in a downstream repository, you **must**:
1. Depend on this core library by adding `orchestrator_core @ git+https://github.com/your-org/ml-orchestrator-hub.git@main` to your dependencies.
2. Use `orchestrator_core.ledger.log_experiment()` at the end of every training run to generate `experiments/latest_run.json`.
3. Use the CLI tool `orchestrator-sync` provided by this hub (or the reusable `.github/workflows/reusable-experiment.yml`) to automatically sync `experiments/latest_run.json` to the central ledger.

### 2. Code Style and Quality
- **Python Version**: This package targets Python 3.10+.
- **Formatting and Linting**: All code must comply with `ruff`. Use `ruff check .` to check for violations and `ruff format .` to format files.
- **Typing**: Strict type hints are required for all newly added functions, classes, and methods.

### 3. Testing
- Every new feature, solver, or metric must have corresponding comprehensive tests added under the `tests/` directory.
- We use `pytest` for running unit tests. Ensure `pytest -v` completes successfully without errors before making any commits.

### 4. Usage
- The package is set up using standard `pyproject.toml`.
- Installation is done via:
  ```bash
  pip install -e .
  # for dev dependencies:
  pip install -e .[dev]
  ```

### 5. Extending the Library
- **Metrics**: Adding new solvers or metrics to `metrics.py` requires numerical stability checks (prevent overflow/underflow, handle extreme distributions).
- **Core modules**: Keep external dependencies limited to the standard ML stack (`numpy`, `pandas`, `scipy`, `scikit-learn`). Introduce new heavy dependencies only when absolutely necessary and specify them in `pyproject.toml`.
