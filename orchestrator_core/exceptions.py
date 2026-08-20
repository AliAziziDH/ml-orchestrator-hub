class RemitConsumeConflict(Exception):
    """
    Raised when a Compare-and-Swap (CAS) Idempotency lock cannot be acquired
    because the event (checkpoint) has already been consumed.
    """

    pass
