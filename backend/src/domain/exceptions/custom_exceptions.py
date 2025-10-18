"""Custom exceptions for the fact-checking system."""

from typing import Optional, Dict, Any


class FactCheckerException(Exception):
    """Base exception for all fact-checker related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.

        Args:
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details
        }


# Audio and Transcription Exceptions
class AudioCaptureError(FactCheckerException):
    """Raised when audio capture fails."""
    pass


class TranscriptionError(FactCheckerException):
    """Raised when transcription fails."""
    pass


class STTServiceError(TranscriptionError):
    """Raised when STT service encounters an error."""
    pass


# NLP and Claim Processing Exceptions
class ClaimExtractionError(FactCheckerException):
    """Raised when claim extraction fails."""
    pass


class SentenceAggregationError(FactCheckerException):
    """Raised when sentence aggregation fails."""
    pass


class TextProcessingError(FactCheckerException):
    """Raised for general text processing errors."""
    pass


# Fact-Checking Exceptions
class FactCheckingError(FactCheckerException):
    """Raised when fact-checking process fails."""
    pass


class EvidenceSearchError(FactCheckingError):
    """Raised when evidence search fails."""
    pass


class VerificationError(FactCheckingError):
    """Raised when claim verification fails."""
    pass


# External Service Exceptions
class ExternalServiceError(FactCheckerException):
    """Base class for external service errors."""

    def __init__(self, service_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize external service error.

        Args:
            service_name: Name of the external service
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message, details)
        self.service_name = service_name
        if self.details is not None:
            self.details["service"] = service_name


class GroqAPIError(ExternalServiceError):
    """Raised when Groq API calls fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("Groq", message, details)


class ExaAPIError(ExternalServiceError):
    """Raised when Exa API calls fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("Exa", message, details)


# WebSocket and Connection Exceptions
class WebSocketError(FactCheckerException):
    """Base class for WebSocket related errors."""
    pass


class ConnectionManagerError(WebSocketError):
    """Raised when connection management fails."""
    pass


class MessageBroadcastError(WebSocketError):
    """Raised when message broadcasting fails."""
    pass


# Configuration and Initialization Exceptions
class ConfigurationError(FactCheckerException):
    """Raised when configuration is invalid or missing."""
    pass


class ServiceInitializationError(FactCheckerException):
    """Raised when a service fails to initialize."""
    pass


class DependencyError(FactCheckerException):
    """Raised when a required dependency is not available."""
    pass


# Timeout and Rate Limiting Exceptions
class TimeoutError(FactCheckerException):
    """Raised when an operation times out."""

    def __init__(self, operation: str, timeout_seconds: float):
        super().__init__(
            f"Operation '{operation}' timed out after {timeout_seconds} seconds",
            {"operation": operation, "timeout": timeout_seconds}
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class RateLimitError(FactCheckerException):
    """Raised when rate limit is exceeded."""

    def __init__(self, service: str, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded for {service}"
        details = {"service": service}

        if retry_after:
            message += f". Retry after {retry_after} seconds"
            details["retry_after"] = retry_after

        super().__init__(message, details)
        self.service = service
        self.retry_after = retry_after