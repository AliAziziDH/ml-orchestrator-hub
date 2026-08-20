from orchestrator_core.state import Phase4AgentState


def evaluate_yield_point(state: Phase4AgentState, epsilon: float = 1e-4) -> str:
    cost = state["cost_tracker"].accumulated_cost_usd
    budget_limit = state["cost_tracker"].budget_limit_usd
    attempts = state["attempts"]
    stall_rounds = state["telemetry"].stall_rounds
    fold_scores = state["telemetry"].fold_scores

    # 1. Budget Limit Exhaustion Check
    if cost >= budget_limit:
        state["cost_tracker"].is_budget_exhausted = True
        state["circuit_breaker_triggered"] = True
        state["error_message"] = (
            f"CRITICAL: Budget limit of ${budget_limit} exhausted. Current cost: ${cost:.4f}."
        )
        return "antigravity_recovery"

    # 2. State Oscillation / Idle Loop Check
    if stall_rounds >= 3:
        state["circuit_breaker_triggered"] = True
        state["error_message"] = (
            f"CRITICAL: State oscillation detected. Jules stalled for {stall_rounds} rounds with the same footprint."
        )
        return "antigravity_recovery"

    # 3. Optimization Stagnation Check
    if attempts > 2 and len(fold_scores) >= 2:
        delta = abs(fold_scores[-2] - fold_scores[-1])
        if delta <= epsilon:
            state["circuit_breaker_triggered"] = True
            state["error_message"] = (
                f"CRITICAL: Stagnation detected. Metric delta ({delta:.6f}) <= epsilon ({epsilon})."
            )
            return "antigravity_recovery"

    # 4. Hard Max Attempts Check
    if attempts >= 5:
        state["circuit_breaker_triggered"] = True
        state["error_message"] = (
            f"CRITICAL: Max attempts ({attempts}) exceeded without convergence."
        )
        return "antigravity_recovery"

    if state["experiment"].status == "SUCCESS":
        return "success"

    return "jules_retry"
