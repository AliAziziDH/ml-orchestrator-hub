import argparse
import hashlib
import hmac
import os
import sys


def generate_email_template(thread_id: str, checkpoint_id: str) -> None:
    """
    Generates a cryptographically signed email template.
    Matches orchestrator_core/email_listener.py implementation exactly.
    """
    secret = os.environ.get("ORCHESTRA_HMAC_SECRET")
    if not secret:
        raise ValueError("CRITICAL ERROR: ORCHESTRA_HMAC_SECRET environment variable is not set. Cryptographic operations aborted.")

    message = f"{thread_id}:{checkpoint_id}".encode()
    secret_bytes = secret.encode("utf-8")
    signature = hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()

    token = f"<orch-{thread_id}-{checkpoint_id}-{signature}@orchestra.ai>"

    body = (
        "APPROVE: Start the baseline SLSQP optimization run for EXP-HP-001 on house-prices-kaggle. "
        "Set folds=10 and learning_rate=0.05. Ensure all downstream telemetry signals are synced to the active Google Sheets ledger."
    )

    template = f"""
From: ali@ali-antigravity.io
To: spark-webhook@ali-antigravity-hub-2026.iam.gserviceaccount.com
Subject: Re: [SUSPENDED] Action Required: SLSQP Weight Optimization ({thread_id})
In-Reply-To: {token}
References: {token}

{body}
"""
    print(template.strip())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a signed email template to trigger pipeline.")
    parser.add_argument(
        "--thread-id",
        type=str,
        default="thread_phase7_kaggle_hp",
        help="The thread ID for the orchestrator (default: thread_phase7_kaggle_hp)",
    )
    parser.add_argument(
        "--checkpoint-id",
        type=str,
        default="ckpt_slsqp_init_gate",
        help="The checkpoint ID to unlock (default: ckpt_slsqp_init_gate)",
    )

    args = parser.parse_args()

    try:
        generate_email_template(args.thread_id, args.checkpoint_id)
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
