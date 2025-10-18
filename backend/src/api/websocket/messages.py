"""WebSocket message factory and types."""

from datetime import datetime
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass, asdict
from enum import Enum


class MessageType(str, Enum):
    """WebSocket message types."""
    CONNECTION = "connection"
    TRANSCRIPT = "transcript"
    VERDICT = "verdict"
    ERROR = "error"


class VerdictStatus(str, Enum):
    """Verdict status types."""
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    UNCLEAR = "unclear"
    NOT_FOUND = "not_found"


@dataclass
class TranscriptData:
    """Transcript message data."""
    text: str
    speaker: str = "Speaker"
    is_final: bool = True


@dataclass
class VerdictData:
    """Verdict message data."""
    transcript: str
    claim: str
    status: str
    confidence: float
    rationale: str
    speaker: str
    evidence_url: Optional[str] = None


@dataclass
class ConnectionData:
    """Connection message data."""
    action: str
    message: str


class MessageFactory:
    """Factory for creating consistent WebSocket messages."""

    @staticmethod
    def create_timestamp() -> str:
        """Create ISO format timestamp."""
        return datetime.now().isoformat()

    @classmethod
    def create_connection_message(
        cls,
        action: Literal["connected", "disconnected", "error"] = "connected",
        message: str = "Successfully connected to fact-checker backend"
    ) -> Dict[str, Any]:
        """
        Create a connection status message.

        Args:
            action: Connection action type
            message: Human-readable status message

        Returns:
            Formatted connection message
        """
        return {
            "type": MessageType.CONNECTION,
            "action": action,
            "message": message,
            "timestamp": cls.create_timestamp()
        }

    @classmethod
    def create_transcript_message(
        cls,
        text: str,
        speaker: str = "Speaker",
        is_final: bool = True
    ) -> Dict[str, Any]:
        """
        Create a transcript message.

        Args:
            text: Transcribed text
            speaker: Speaker identifier
            is_final: Whether transcription is final

        Returns:
            Formatted transcript message
        """
        return {
            "type": MessageType.TRANSCRIPT,
            "timestamp": cls.create_timestamp(),
            "data": {
                "text": text,
                "speaker": speaker,
                "is_final": is_final
            }
        }

    @classmethod
    def create_verdict_message(
        cls,
        transcript: str,
        claim: str,
        status: str,
        confidence: float,
        rationale: str,
        speaker: str,
        evidence_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a verdict message.

        Args:
            transcript: Original transcript containing the claim
            claim: The extracted claim text
            status: Verdict status
            confidence: Confidence score (0-1)
            rationale: Explanation of the verdict
            speaker: Speaker who made the claim
            evidence_url: Optional URL to supporting evidence

        Returns:
            Formatted verdict message
        """
        return {
            "type": MessageType.VERDICT,
            "timestamp": cls.create_timestamp(),
            "data": {
                "transcript": transcript,
                "claim": claim,
                "status": status,
                "confidence": confidence,
                "rationale": rationale,
                "evidence_url": evidence_url,
                "speaker": speaker
            }
        }

    @classmethod
    def create_error_message(
        cls,
        error: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an error message.

        Args:
            error: Error description
            details: Optional additional error details

        Returns:
            Formatted error message
        """
        message = {
            "type": MessageType.ERROR,
            "timestamp": cls.create_timestamp(),
            "error": error
        }

        if details:
            message["details"] = details

        return message

    @classmethod
    def from_verdict_model(cls, verdict, transcript: str, claim_text: str, speaker: str) -> Dict[str, Any]:
        """
        Create a verdict message from a verdict model instance.

        Args:
            verdict: FactCheckVerdict model instance
            transcript: Original transcript
            claim_text: The claim text
            speaker: Speaker identifier

        Returns:
            Formatted verdict message
        """
        return cls.create_verdict_message(
            transcript=transcript,
            claim=claim_text,
            status=verdict.status,
            confidence=verdict.confidence,
            rationale=verdict.rationale,
            speaker=speaker,
            evidence_url=verdict.evidence_url
        )