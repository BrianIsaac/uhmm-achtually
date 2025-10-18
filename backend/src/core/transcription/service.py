"""Transcription service for managing audio-to-text conversion."""

from typing import Optional, Callable, Awaitable
from loguru import logger

from src.processors.audio_stream_processor import AudioStreamProcessor
from src.services.stt import GroqSTT


class TranscriptionService:
    """
    Service for managing audio transcription.

    This service coordinates between audio capture and speech-to-text processing.
    """

    def __init__(
        self,
        stt_service: GroqSTT,
        on_transcription: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        """
        Initialize the transcription service.

        Args:
            stt_service: Speech-to-text service
            on_transcription: Optional callback for transcription results
        """
        self.stt_service = stt_service
        self.on_transcription = on_transcription
        self.audio_processor: Optional[AudioStreamProcessor] = None
        self.is_running = False

    def set_transcription_callback(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """
        Set the callback for transcription results.

        Args:
            callback: Async function to call with transcription results
        """
        self.on_transcription = callback

        # Update audio processor callback if it exists
        if self.audio_processor:
            self.audio_processor.on_transcription = callback

    async def start(self) -> None:
        """Start the transcription service."""
        if self.is_running:
            logger.warning("Transcription service already running")
            return

        if not self.on_transcription:
            raise ValueError("No transcription callback set")

        # Initialize audio processor
        self.audio_processor = AudioStreamProcessor(
            stt=self.stt_service,
            on_transcription=self.on_transcription
        )

        await self.audio_processor.start()
        self.is_running = True
        logger.info("Transcription service started")

    async def stop(self) -> None:
        """Stop the transcription service."""
        if not self.is_running:
            logger.warning("Transcription service not running")
            return

        if self.audio_processor:
            await self.audio_processor.stop()
            self.audio_processor = None

        self.is_running = False
        logger.info("Transcription service stopped")

    async def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """
        Directly transcribe audio data.

        Args:
            audio_data: Audio data to transcribe

        Returns:
            Transcribed text or None if failed
        """
        try:
            result = await self.stt_service.transcribe(audio_data)
            return result
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}", exc_info=True)
            return None