class RemitConsumeConflict(Exception):
    """
    Raised when a Compare-and-Swap (CAS) Idempotency lock cannot be acquired
    because the event (checkpoint) has already been consumed.
    """


class WebhookSecurityError(Exception):
    """
    Raised when a webhook security check fails (e.g., HMAC signature validation failure, DKIM failure).
    """
