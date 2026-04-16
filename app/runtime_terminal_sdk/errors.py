from __future__ import annotations


class RuntimeTerminalError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        method: str | None = None,
        path: str | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.path = path
        self.response_text = response_text


class RuntimeTerminalNotFoundError(RuntimeTerminalError):
    pass


class RuntimeTerminalConflictError(RuntimeTerminalError):
    pass


class RuntimeTerminalValidationError(RuntimeTerminalError):
    pass


class RuntimeTerminalServerError(RuntimeTerminalError):
    pass


class RuntimeTerminalTransportError(RuntimeTerminalError):
    pass
