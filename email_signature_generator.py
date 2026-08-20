import hashlib
import hmac
import os


def generate_secure_message_id(
    thread_id: str, checkpoint_id: str, secret_key: str, domain: str = "ali-antigravity.io"
) -> str:
    """
    Generates a secure, HMAC-SHA256 signed Message-ID to be embedded in SMTP In-Reply-To/References headers.
    This prevents hijacking and context manipulation in the Email Listener Gateway [5, 56, 95].
    """
    # 1. Create the token payload
    payload = f"{thread_id}:{checkpoint_id}"

    # 2. Compute HMAC-SHA256 signature
    signature = hmac.new(
        secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()[:16]  # Keep it compact but cryptographically secure

    # 3. Format as a standards-compliant Message-ID header [186]
    message_id = f"<{thread_id}.{checkpoint_id}.{signature}@{domain}>"
    return message_id


if __name__ == "__main__":
    # Example configurations representing Phase 7 Launch Parameters
    THREAD_ID = "thread_phase7_kaggle_hp"
    CHECKPOINT_ID = "ckpt_slsqp_init_gate"
    SECRET_KEY = os.getenv("ORCHESTRA_HMAC_SECRET", "super_secret_orchestra_salt_2026")
    DOMAIN = "ali-antigravity.io"

    msg_id = generate_secure_message_id(THREAD_ID, CHECKPOINT_ID, SECRET_KEY, DOMAIN)

    print("=" * 80)
    print("ORCHESTRA SECURITY WORKFLOW: SECURE EMAIL MESSAGE-ID GENERATOR")
    print("=" * 80)
    print(f"[*] Thread ID:      {THREAD_ID}")
    print(f"[*] Checkpoint ID:  {CHECKPOINT_ID}")
    print("[*] Secure Message-ID (To put in In-Reply-To & References headers):")
    print(f"    {msg_id}")
    print("\n" + "=" * 80)
    print("FORMULATED LIVE SMTP EMAIL COMMAND TEMPLATE")
    print("=" * 80)
    print(
        "From:          Conductor <ali@ali-antigravity.io> (Strictly authorized & DKIM-signed) [186]"
    )
    print(
        "To:            Orchestra Inbound Parser <spark-webhook@ali-antigravity-hub-2026.iam.gserviceaccount.com>"
    )
    print(
        f"Subject:       Re: [SUSPENDED] Action Required: SLSQP Weight Optimization ({THREAD_ID})"
    )
    print(f"In-Reply-To:   {msg_id}")
    print(f"References:    {msg_id}")
    print("-" * 80)
    print("Body Content (Plain Text):")
    print("-" * 80)
    print(
        "APPROVE: Start the baseline SLSQP optimization run for EXP-HP-001 on house-prices-kaggle."
    )
    print("Set folds=10 and learning_rate=0.05.")
    print("Ensure all downstream telemetry signals are synced to the active Google Sheets ledger.")
    print("=" * 80)
