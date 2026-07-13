from __future__ import annotations


class ApiError(Exception):
    """Structured API error raised from handlers and dependencies.

    Caught by the exception handler in api/main.py and serialized
    as ErrorEnvelope with the correct HTTP status code.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        detail: str | None = None,
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.detail = detail
        self.field_errors = field_errors
