class RuntimeConflictError(RuntimeError):
    """Runtime transaction-level conflict."""


class RuntimeLeaseConflictError(RuntimeConflictError):
    """Lease / claim token dual-consistency validation failed."""


class RuntimeStateConflictError(RuntimeConflictError):
    """State transition is not allowed under current runtime state."""
