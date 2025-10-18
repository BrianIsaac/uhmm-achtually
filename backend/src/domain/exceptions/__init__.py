"""Domain exceptions module."""

from src.domain.exceptions.custom_exceptions import (
    # Base
    FactCheckerException,

    # Audio and Transcription
    AudioCaptureError,
    TranscriptionError,
    STTServiceError,

    # NLP and Claims
    ClaimExtractionError,
    SentenceAggregationError,
    TextProcessingError,

    # Fact-Checking
    FactCheckingError,
    EvidenceSearchError,
    VerificationError,

    # External Services
    ExternalServiceError,
    GroqAPIError,
    ExaAPIError,

    # WebSocket
    WebSocketError,
    ConnectionManagerError,
    MessageBroadcastError,

    # Configuration
    ConfigurationError,
    ServiceInitializationError,
    DependencyError,

    # Timeout and Rate Limiting
    TimeoutError,
    RateLimitError,
)

__all__ = [
    "FactCheckerException",
    "AudioCaptureError",
    "TranscriptionError",
    "STTServiceError",
    "ClaimExtractionError",
    "SentenceAggregationError",
    "TextProcessingError",
    "FactCheckingError",
    "EvidenceSearchError",
    "VerificationError",
    "ExternalServiceError",
    "GroqAPIError",
    "ExaAPIError",
    "WebSocketError",
    "ConnectionManagerError",
    "MessageBroadcastError",
    "ConfigurationError",
    "ServiceInitializationError",
    "DependencyError",
    "TimeoutError",
    "RateLimitError",
]