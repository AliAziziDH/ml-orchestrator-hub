import base64
import json
import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from orchestrator_core.state import AgentState


class DecisionAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    FEEDBACK_RETRY = "FEEDBACK_RETRY"
    SAGA_ROLLBACK = "SAGA_ROLLBACK"


class ParsedDecision(BaseModel):
    action: DecisionAction
    feedback: str
    target_stage: str | None = None
    raw_text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmailNotificationFormatter:
    @staticmethod
    def format_approval_email(
        state: AgentState, thread_id: str, checkpoint_id: str
    ) -> dict[str, str]:
        experiment_ledger = state.get("experiment_ledger") or {}
        summary = experiment_ledger.get("summary")
        if not summary:
            # Fallback
            summary = state.get("current_stage", "Model Approval Review")

        metrics_delta = experiment_ledger.get("metrics_delta")
        if not metrics_delta:
            metrics_delta = experiment_ledger

        # Formulate HTML table
        rows = []
        for k, v in metrics_delta.items():
            if isinstance(v, (str, int, float, bool)):
                rows.append(f"<tr><td>{k}</td><td>{v}</td></tr>")

        if rows:
            table_html = (
                f"<table border='1'><tr><th>Metric</th><th>Value</th></tr>{''.join(rows)}</table>"
            )
        else:
            table_html = "<p>No metrics available.</p>"

        # Security Token
        token_data = {"thread_id": thread_id, "checkpoint_id": checkpoint_id}
        token = base64.urlsafe_b64encode(json.dumps(token_data).encode()).decode()

        html_body = f"""
<html>
<body>
    <h2>Executive Summary</h2>
    <p>{summary}</p>
    <h2>Metrics Delta</h2>
    {table_html}
    <!-- SEC_TOKEN: {token} -->
</body>
</html>
""".strip()

        text_body = f"Executive Summary:\n{summary}\n\nMetrics:\n"
        for k, v in metrics_delta.items():
            if isinstance(v, (str, int, float, bool)):
                text_body += f"{k}: {v}\n"

        return {
            "subject": f"[Action Required] Approval Needed: {summary}",
            "html_body": html_body,
            "text_body": text_body.strip(),
        }


class DecisionParser:
    @staticmethod
    def parse_reply_text(raw_reply: str) -> ParsedDecision:
        text = raw_reply.strip()

        # Word boundary regexes
        approve_pattern = re.compile(
            r"\b(approve|approved|ok|yes|lgtm|confirm|accept)\b", re.IGNORECASE
        )
        reject_pattern = re.compile(r"\b(reject|rejected|no|cancel|decline|stop)\b", re.IGNORECASE)
        rollback_pattern = re.compile(r"\b(rollback|revert|undo|abort)\b", re.IGNORECASE)

        if rollback_pattern.search(text):
            action = DecisionAction.SAGA_ROLLBACK
        elif reject_pattern.search(text):
            action = DecisionAction.REJECT
        elif approve_pattern.search(text):
            action = DecisionAction.APPROVE
        else:
            action = DecisionAction.FEEDBACK_RETRY

        return ParsedDecision(
            action=action,
            feedback=text,
            raw_text=raw_reply,
            timestamp=datetime.now(timezone.utc),
        )
