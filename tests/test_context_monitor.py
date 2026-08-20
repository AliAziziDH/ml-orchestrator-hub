import pytest
from orchestrator_core.context_monitor import ContextTokenMonitor
from orchestrator_core.cost import TokenCostLedger


def test_context_monitor_below_threshold():
    monitor = ContextTokenMonitor(max_context_limit=10000)
    ledger = TokenCostLedger()

    # 50% limit (5000 tokens out of 10000) -> should_compact=False
    # 60% threshold is 6000 tokens
    prompt_tokens = 3000
    completion_tokens = 2000

    should_compact = monitor.analyze_usage(prompt_tokens, completion_tokens, ledger)

    assert should_compact is False
    assert ledger.input_tokens == 3000
    assert ledger.output_tokens == 2000

    # Cost should be (3 * 0.00125) + (2 * 0.00375) = 0.00375 + 0.0075 = 0.01125
    expected_cost = (3000 / 1000.0) * 0.00125 + (2000 / 1000.0) * 0.00375
    assert ledger.accumulated_cost_usd == pytest.approx(expected_cost)


def test_context_monitor_above_threshold():
    monitor = ContextTokenMonitor(max_context_limit=10000)
    ledger = TokenCostLedger()

    # 65% limit (6500 tokens out of 10000) -> should_compact=True
    # 60% threshold is 6000 tokens
    prompt_tokens = 4000
    completion_tokens = 2500

    should_compact = monitor.analyze_usage(prompt_tokens, completion_tokens, ledger)

    assert should_compact is True
    assert ledger.input_tokens == 4000
    assert ledger.output_tokens == 2500


def test_context_monitor_default_limit(monkeypatch):
    monkeypatch.delenv("ORCHESTRA_MAX_CONTEXT", raising=False)
    monitor = ContextTokenMonitor()
    assert monitor.max_context_limit == 128000

    monkeypatch.setenv("ORCHESTRA_MAX_CONTEXT", "200000")
    monitor_env = ContextTokenMonitor()
    assert monitor_env.max_context_limit == 200000
