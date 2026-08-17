# AGENTS.md

## Architectural Guidelines and Operational Rules for this Repository

Welcome to the `orchestrator_core` repository. If you are an AI agent operating inside this repo, you must adhere to the following rules:

### 1. Code Style and Quality
- **Python Version**: This package targets Python 3.10+.
- **Formatting and Linting**: All code must comply with `ruff`. Use `ruff check .` to check for violations and `ruff format .` to format files.
- **Typing**: Strict type hints are required for all newly added functions, classes, and methods.

### 2. Testing
- Every new feature, solver, or metric must have corresponding comprehensive tests added under the `tests/` directory.
- We use `pytest` for running unit tests. Ensure `pytest -v` completes successfully without errors before making any commits.

### 3. Usage
- The package is set up using standard `pyproject.toml`.
- Installation is done via:
  ```bash
  pip install -e .
  # for dev dependencies:
  pip install -e .[dev]
  ```

### 4. Extending the Library
- **Metrics**: Adding new solvers or metrics to `metrics.py` requires numerical stability checks (prevent overflow/underflow, handle extreme distributions).
- **Core modules**: Keep external dependencies limited to the standard ML stack (`numpy`, `pandas`, `scipy`, `scikit-learn`). Introduce new heavy dependencies only when absolutely necessary and specify them in `pyproject.toml`.
