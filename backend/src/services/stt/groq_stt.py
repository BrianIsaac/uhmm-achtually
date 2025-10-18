"""Groq STT service using Whisper models.

Wrapper for Groq's Whisper API for speech-to-text transcription.
"""

import io
import httpx
from typing import Optional
from loguru import logger


class GroqSTT:
    """Groq Speech-to-Text service using Whisper models."""

    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo"):
        """
        Initialize Groq STT service.

        Args:
            api_key: Groq API key
            model: Whisper model to use (default: whisper-large-v3-turbo)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"

    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio data to text using Groq Whisper API.

        Args:
            audio_data: Audio data in WAV format (bytes)
            language: Optional language hint (e.g., "en")

        Returns:
            Transcribed text string

        Raises:
            Exception: If transcription fails
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Prepare multipart form data
                files = {
                    "file": ("audio.wav", io.BytesIO(audio_data), "audio/wav")
                }
                data = {
                    "model": self.model,
                    "response_format": "text"
                }
                if language:
                    data["language"] = language

                headers = {
                    "Authorization": f"Bearer {self.api_key}"
                }

                # Make API request
                response = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    files=files,
                    data=data
                )

                response.raise_for_status()
                transcription = response.text.strip()

                return transcription

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during transcription: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            raise

    async def is_available(self) -> bool:
        """
        Check if the Groq STT service is available.

        Returns:
            True if service is reachable
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return response.status_code == 200
        except Exception:
            return False


__all__ = ["GroqSTT"]
