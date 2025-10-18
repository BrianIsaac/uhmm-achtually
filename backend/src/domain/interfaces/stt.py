"""Speech-to-Text interface."""

from abc import ABC, abstractmethod
from typing import Optional


class ISTTService(ABC):
    """Interface for Speech-to-Text services."""

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Audio data in bytes
            language: Optional language hint

        Returns:
            Transcribed text

        Raises:
            TranscriptionError: If transcription fails
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the STT service is available.

        Returns:
            True if service is available
        """
        pass