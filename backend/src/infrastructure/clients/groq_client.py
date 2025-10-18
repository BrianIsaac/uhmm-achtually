"""Groq API client wrapper."""

from typing import Optional, Dict, Any
from groq import Groq
from loguru import logger

from src.domain.exceptions import GroqAPIError


class GroqClient:
    """Client for interacting with Groq API."""

    def __init__(self, api_key: str):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key
        """
        self.api_key = api_key
        self.client = Groq(api_key=api_key)

    async def transcribe(
        self,
        audio_data: bytes,
        model: str = "whisper-large-v3-turbo",
        language: str = "en"
    ) -> str:
        """
        Transcribe audio using Groq Whisper.

        Args:
            audio_data: Audio data in bytes
            model: Whisper model to use
            language: Language code

        Returns:
            Transcribed text

        Raises:
            GroqAPIError: If transcription fails
        """
        try:
            response = self.client.audio.transcriptions.create(
                model=model,
                file=("audio.wav", audio_data),
                language=language
            )
            return response.text

        except Exception as e:
            logger.error(f"Groq transcription failed: {e}")
            raise GroqAPIError(
                "Failed to transcribe audio",
                {"model": model, "language": language, "error": str(e)}
            )

    async def complete(
        self,
        prompt: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.1,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate text completion using Groq LLM.

        Args:
            prompt: Input prompt
            model: LLM model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            GroqAPIError: If completion fails
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Groq completion failed: {e}")
            raise GroqAPIError(
                "Failed to generate completion",
                {"model": model, "prompt_length": len(prompt), "error": str(e)}
            )