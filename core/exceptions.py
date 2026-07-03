class BaseAuditException(Exception):
    """Base exception for all audit-related errors.

    Subclasses should provide a clear, user‑facing message and optional
    contextual data. The `code` attribute can be used for programmatic
    handling (e.g., error categorisation).
    """

    code: str = "BASE_ERROR"
    message: str = "An audit error occurred."

    def __init__(self, message: str | None = None, **context):
        self.message = message or self.message
        self.context = context
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Serialise the exception for logging or API responses."""
        return {
            "code": self.code,
            "message": self.message,
            "context": self.context,
        }


class ValidationError(BaseAuditException):
    code = "VALIDATION_ERROR"
    message = "Data validation failed."


class LLMProviderError(BaseAuditException):
    code = "LLM_PROVIDER_ERROR"
    message = "Error interacting with the LLM provider."


class ConfigurationError(BaseAuditException):
    code = "CONFIGURATION_ERROR"
    message = "Invalid configuration detected."

# Add more specific exceptions as the project grows.
