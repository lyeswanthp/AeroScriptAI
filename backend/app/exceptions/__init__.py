"""Custom exceptions for the backend."""


class AppException(Exception):
    """Base exception with error code."""

    def __init__(self, message: str, code: str, detail: str | None = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)


class LMStudioUnavailableError(AppException):
    """Raised when LM Studio is unreachable or returns an error."""

    def __init__(self, message: str = "LM Studio is unavailable", detail: str | None = None):
        super().__init__(message, "LM_STUDIO_UNAVAILABLE", detail)


class ImageValidationError(AppException):
    """Raised when an image fails validation."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message, "IMAGE_VALIDATION_ERROR", detail)


class SessionNotFoundError(AppException):
    """Raised when a session ID does not exist."""

    def __init__(self, session_id: str):
        super().__init__(
            f"Session '{session_id}' not found",
            "SESSION_NOT_FOUND",
            f"Session may have expired or does not exist"
        )


class SessionLimitExceededError(AppException):
    """Raised when too many active sessions exist."""

    def __init__(self):
        super().__init__(
            "Too many active sessions",
            "SESSION_LIMIT_EXCEEDED",
            "Please end an existing session before starting a new one"
        )


class ModelBusyError(AppException):
    """Raised when the model is processing another request."""

    def __init__(self):
        super().__init__(
            "Model is currently busy",
            "MODEL_BUSY",
            "Please wait and try again"
        )


class PreprocessingError(AppException):
    """Raised when image preprocessing fails."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message, "PREPROCESSING_ERROR", detail)
