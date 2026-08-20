from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# =====================================================================
# ۱. ساختار داده‌ای ترازیابی مالی (بروزرسانی شده بر اساس اصول فاز ۵ و ۶)
# =====================================================================
class TokenCostLedger(BaseModel):
    input_tokens: int = Field(default=0, description="تعداد توکن‌های ورودی مصرف‌شده")
    output_tokens: int = Field(default=0, description="تعداد توکن‌های خروجی تولیدشده")
    accumulated_cost_usd: float = Field(default=0.0, description="هزینه دلاری تجمیعی")
    budget_limit_usd: float = Field(default=5.0, description="سقف بودجه مجاز")
    is_budget_exhausted: bool = Field(default=False, description="قطع‌کننده جریان مالی")


# نرخ‌های فرضی برای محاسبه دقیق هزینه‌ها در سال ۲۰۲۶
MODEL_PRICING = {
    "gemini-1.5-pro": {"input": 0.00125 / 1000, "output": 0.00375 / 1000},
    "gemini-1.5-flash": {"input": 0.000075 / 1000, "output": 0.0003 / 1000},
    "claude-3-5-sonnet": {"input": 0.003 / 1000, "output": 0.015 / 1000},
}


# =====================================================================
# ۲. پیاده‌سازی مانیتور و حسابرس هوشمند کانتکست (Context Token Monitor)
# =====================================================================
class ContextTokenMonitor:
    """
    Core middleware engine to track token consumption and enforce budget caps
    during LangGraph Suspend/Resume lifecycles inside the Orchestra framework.
    """

    def __init__(self, ledger: TokenCostLedger, default_model: str = "gemini-1.5-pro"):
        self.ledger = ledger
        self.default_model = default_model

    def audit_llm_call(
        self, model_name: str, prompt_tokens: int, completion_tokens: int
    ) -> TokenCostLedger:
        """
        Intercepts LLM execution metadata, calculates exact financial costs,
        and dynamically updates the TokenCostLedger state.
        """
        pricing = MODEL_PRICING.get(model_name, MODEL_PRICING[self.default_model])

        # ۱. به‌روزرسانی شمارنده‌های اتمیک توکن
        self.ledger.input_tokens += prompt_tokens
        self.ledger.output_tokens += completion_tokens

        # ۲. محاسبه هزینه دلاری این استپ محاسباتی
        step_cost = (prompt_tokens * pricing["input"]) + (completion_tokens * pricing["output"])
        self.ledger.accumulated_cost_usd += step_cost

        # ۳. بررسی وضعیت سقف بودجه (قطع‌کننده جریان)
        if self.ledger.accumulated_cost_usd >= self.ledger.budget_limit_usd:
            self.ledger.is_budget_exhausted = True

        return self.ledger

    def check_compaction_trigger(
        self, current_context_tokens: int, max_context_limit: int
    ) -> dict[str, Any]:
        """
        Applies the SOTA 40-60% Context Rule. Triggers proactive compaction
        before reaching the model's performance cliff (Context Rot).
        """
        utilization_ratio = current_context_tokens / max_context_limit
        should_compact = utilization_ratio >= 0.60

        return {
            "utilization_percentage": utilization_ratio * 100,
            "should_compact": should_compact,
            "compaction_level": "URGENT"
            if utilization_ratio >= 0.85
            else "PROACTIVE"
            if should_compact
            else "NONE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def log_suspend_resume_overhead(
        self, suspend_ckpt_tokens: int, resume_input_tokens: int
    ) -> dict[str, Any]:
        """
        Computes the serialization/deserialization overhead of thread suspension.
        Tracks if repeated interrupts are causing context amplification.
        """
        overhead_delta = resume_input_tokens - suspend_ckpt_tokens
        return {
            "suspend_tokens": suspend_ckpt_tokens,
            "resume_tokens": resume_input_tokens,
            "overhead_delta": overhead_delta,
            "is_amplified": overhead_delta > 1000,  # هشدار در صورت انباشت کانتکست
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# =====================================================================
# ۳. اجرای آزمایش صحت عملکرد داخلی (Unit Verification)
# =====================================================================
if __name__ == "__main__":
    # ایجاد یک لجر نمونه با بودجه محدود ۰.۹ دلار برای به صدا درآوردن فیوز امنیتی
    sample_ledger = TokenCostLedger(budget_limit_usd=0.90)
    monitor = ContextTokenMonitor(ledger=sample_ledger)

    # شبیه‌سازی یک فراخوانی بزرگ با مدل Claude 3.5 Sonnet
    print("Executing simulated LLM call audit...")
    updated_ledger = monitor.audit_llm_call(
        model_name="claude-3-5-sonnet",
        prompt_tokens=250000,  # ۲۵۰ هزار توکن ورودی -> ۰.۷۵ دلار
        completion_tokens=15000,  # ۱۵ هزار توکن خروجی -> ۰.۲۲۵ دلار
    )

    # هزینه مجموع = ۰.۹۷۵ دلار (بیشتر از بودجه مجاز ۰.۹۰ دلاری)
    print(f"Total Cost: ${updated_ledger.accumulated_cost_usd:.4f} USD")
    print(f"Is Circuit Breaker Triggered? {updated_ledger.is_budget_exhausted}")
    assert updated_ledger.is_budget_exhausted, "Circuit breaker should be triggered!"

    # تست فعال‌سازی قانون ۴۰-۶۰٪
    compaction_report = monitor.check_compaction_trigger(
        current_context_tokens=120000, max_context_limit=200000
    )
    print(f"Compaction Report: {compaction_report}")
    assert compaction_report["should_compact"]
    print("\n[SUCCESS] ContextTokenMonitor verified successfully.")
